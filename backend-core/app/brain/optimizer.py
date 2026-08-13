"""
The optimizer — makes the kernel measure itself and say what to change.

Written for the two machines this actually has to run on: a 4-core CPU laptop
with no discrete GPU, and a Galaxy S10. Both are memory- and compute-bound, and
on both the difference between a usable assistant and an unusable one is a small
number of decisions. So this measures those decisions rather than guessing.

What it deliberately does NOT do, because none of it applies here:

  * FlashAttention-2 — a CUDA kernel. There is no CUDA device on either target.
    Ollama on CPU uses llama.cpp's own attention path; there is nothing to swap.
  * TGI / vLLM — GPU inference servers, several GB of runtime, CUDA-only for the
    fast paths. On a 4-core CPU they are slower than llama.cpp, and they do not
    run on Android at all.
  * "Adding a KV cache" — llama.cpp already keeps one per session. The knobs
    that exist are how long the model stays resident (`keep_alive`) and how big
    the context is (`num_ctx`); both are measured below.

What actually moves the number, in the order it moved it here:

  1. Not repeating work.       A tool loop that re-ran the same call cost 4x.
  2. Prompt size.              12 tool specs cost more than the answer did.
  3. Model size and quant.     3B-Q4 answers in a tenth of 7B-Q4's time.
  4. Keeping the model warm.   A cold load is minutes; a warm one is seconds.

The probes below measure the four knobs Ollama actually exposes — `num_ctx`,
`num_thread`, `num_batch`, `keep_alive` — plus the cost of swapping a model in
and out of RAM. They are slow and explicit: none of them runs at boot, because
each one occupies the machine it is measuring.

Every number comes from Ollama's own counters (`prompt_eval_duration`,
`eval_count`, `eval_duration`) rather than wall time wherever the distinction
matters. Wall time carries loading and queueing, so it answers "how long did I
wait", while the counters answer "which knob caused it" — and only the second
can be tuned.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger("sexta-feira.optimizer")

# A prompt short enough that the reply cost is dominated by the model, not by
# what we asked. Optimising against a long prompt measures the prompt.
PROBE = "Responda apenas com a palavra: pronto."

# Rough RAM ceilings. The S10 has 8 GB total with maybe 3 GB free to an app;
# anything above that swaps and the assistant stops being usable at all.
TARGET_BUDGETS_GB = {"s10": 3.0, "cpu-laptop": 6.0}


@dataclass
class ModelProbe:
    name: str
    size_gb: float
    quantization: str
    capabilities: list[str]
    loaded: bool
    cold_load_s: float | None = None
    warm_reply_s: float | None = None
    tokens_per_s: float | None = None
    error: str | None = None


@dataclass
class ContextPoint:
    """One rung of the context-window ladder."""
    tokens: int
    prefill_s: float
    ms_per_token: float


@dataclass
class ThreadPoint:
    threads: int
    tokens_per_s: float


@dataclass
class BatchPoint:
    num_batch: int
    texts_per_s: float


@dataclass
class SwapCost:
    model: str
    cold_load_s: float
    warm_reply_s: float
    swap_penalty_s: float


@dataclass
class Report:
    endpoint: str
    host_cores: int
    host_ram_gb: float
    models: list[ModelProbe] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "host": {"cores": self.host_cores, "ram_gb": round(self.host_ram_gb, 1)},
            "models": [asdict(m) for m in self.models],
            "findings": self.findings,
            "actions": self.actions,
        }


class Optimizer:
    """Measures the local inference setup and reports what to change."""

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = (endpoint or settings.ollama_endpoint).rstrip("/")

    # ---------- measurement ----------

    async def _tags(self, c: httpx.AsyncClient) -> list[dict]:
        r = await c.get("/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])

    async def _capabilities(self, c: httpx.AsyncClient, model: str) -> list[str]:
        """What Ollama says a model can do, e.g. ["completion","tools","vision"].

        It lives on /api/show and NOWHERE else. This used to read
        `m.get("capabilities")` off an /api/tags entry, which has no such field
        — so every model came back capability-less and the three checks in
        `_analyse` that test capabilities ("is the brain the fastest model that
        can do the job", "can the brain act at all", the quantisation sweep over
        chat models) compared against an empty list and could never fire. The
        report looked healthy because it was reporting on nothing.
        """
        try:
            r = await c.post("/api/show", json={"model": model}, timeout=30.0)
            r.raise_for_status()
            return [str(x).lower() for x in (r.json().get("capabilities") or [])]
        except Exception:  # noqa: BLE001 — a model that won't describe itself is not fatal
            return []

    async def _loaded(self, c: httpx.AsyncClient) -> set[str]:
        try:
            r = await c.get("/api/ps")
            r.raise_for_status()
            return {m["name"] for m in r.json().get("models", [])}
        except Exception:  # noqa: BLE001 — older Ollama has no /api/ps
            return set()

    async def _time_reply(self, c: httpx.AsyncClient, model: str) -> tuple[float, float | None]:
        """Seconds to a short reply, and generated tokens per second.

        `eval_count / eval_duration` comes from Ollama itself, so it measures
        generation alone — wall time also carries loading and prompt evaluation,
        which is the number the owner feels but not the one that identifies a
        slow model.
        """
        started = time.perf_counter()
        r = await c.post("/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": PROBE}],
            "stream": False,
            "options": {"num_predict": 16},
        })
        r.raise_for_status()
        wall = time.perf_counter() - started
        body = r.json()
        eval_count = body.get("eval_count")
        eval_ns = body.get("eval_duration")
        tps = (eval_count / (eval_ns / 1e9)) if eval_count and eval_ns else None
        return wall, tps

    async def probe(self, benchmark: bool = True) -> Report:
        import psutil

        report = Report(
            endpoint=self.endpoint,
            host_cores=psutil.cpu_count(logical=True) or 0,
            host_ram_gb=psutil.virtual_memory().total / 1e9,
        )

        async with httpx.AsyncClient(base_url=self.endpoint, timeout=600.0) as c:
            try:
                tags = await self._tags(c)
            except Exception as e:  # noqa: BLE001
                report.findings.append(f"Ollama não respondeu em {self.endpoint}: {e}")
                return report
            loaded = await self._loaded(c)

            for m in tags:
                details = m.get("details") or {}
                probe = ModelProbe(
                    name=m["name"],
                    size_gb=round(m.get("size", 0) / 1e9, 2),
                    quantization=details.get("quantization_level", "?"),
                    capabilities=await self._capabilities(c, m["name"]),
                    loaded=m["name"] in loaded,
                )
                if benchmark and "embedding" not in probe.capabilities:
                    try:
                        was_loaded = probe.loaded
                        wall, tps = await self._time_reply(c, m["name"])
                        probe.tokens_per_s = round(tps, 1) if tps else None
                        if was_loaded:
                            probe.warm_reply_s = round(wall, 1)
                        else:
                            probe.cold_load_s = round(wall, 1)
                            # Now that it is resident, the warm number is real.
                            warm, _ = await self._time_reply(c, m["name"])
                            probe.warm_reply_s = round(warm, 1)
                    except Exception as e:  # noqa: BLE001
                        probe.error = str(e)[:160]
                report.models.append(probe)

        self._analyse(report)
        return report

    # ---------- 1. context window ----------

    async def profile_context(
        self, model: str | None = None, rungs: tuple[int, ...] = (256, 512, 1024, 2048, 4096),
    ) -> tuple[list[ContextPoint], int, list[str]]:
        """Time the READ phase against a growing prompt.

        Prefill is linear in tokens right up to the point where the working set
        stops fitting — then each extra token costs disproportionately more. That
        knee is the useful `num_ctx`: past it the model is paying to read context
        it will not use, and the owner waits for a first token that has nothing
        to do with their question.

        Measured with `prompt_eval_duration`, never wall time: generation and
        model loading are in wall time too, and they would move the knee.
        """
        model = model or settings.brain_model
        points: list[ContextPoint] = []
        notes: list[str] = []

        async with httpx.AsyncClient(base_url=self.endpoint, timeout=900.0) as c:
            for tokens in rungs:
                # A word is roughly a token for this purpose; the exact ratio does
                # not matter because Ollama reports the count it actually read.
                filler = " ".join(["contexto"] * tokens)
                try:
                    r = await c.post("/api/chat", json={
                        "model": model,
                        "messages": [{"role": "user", "content": f"{filler}\n\n{PROBE}"}],
                        "stream": False,
                        "options": {"num_predict": 1, "num_ctx": max(rungs)},
                    })
                    r.raise_for_status()
                    b = r.json()
                except Exception as e:  # noqa: BLE001
                    notes.append(f"num_ctx={tokens} falhou: {str(e)[:120]}")
                    break

                read = b.get("prompt_eval_count") or 0
                dur_ns = b.get("prompt_eval_duration") or 0
                if not read or not dur_ns:
                    notes.append(f"num_ctx={tokens}: Ollama não reportou contadores de leitura")
                    continue
                prefill = dur_ns / 1e9
                points.append(ContextPoint(
                    tokens=read,
                    prefill_s=round(prefill, 2),
                    ms_per_token=round(prefill * 1000 / read, 3),
                ))

        return points, _knee(points), notes

    # ---------- 2. threads ----------

    async def tune_threads(self, model: str | None = None) -> tuple[list[ThreadPoint], int, list[str]]:
        """Generation speed at 1..N threads.

        More threads is not monotonically better on a laptop: past a point the
        cores contend for the same memory bus, and taking the last one leaves the
        OS (and the kernel's own audio, DB and HTTP work) fighting the model for
        it. So the recommendation prefers leaving one core free whenever doing so
        costs less than 5% — a margin below this measurement's own noise.
        """
        import psutil

        model = model or settings.brain_model
        cores = psutil.cpu_count(logical=True) or 1
        points: list[ThreadPoint] = []
        notes: list[str] = []

        async with httpx.AsyncClient(base_url=self.endpoint, timeout=900.0) as c:
            for n in range(1, cores + 1):
                try:
                    r = await c.post("/api/chat", json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Conte de um a vinte."}],
                        "stream": False,
                        "options": {"num_predict": 48, "num_thread": n},
                    })
                    r.raise_for_status()
                    b = r.json()
                except Exception as e:  # noqa: BLE001
                    notes.append(f"num_thread={n} falhou: {str(e)[:120]}")
                    continue
                count, dur = b.get("eval_count"), b.get("eval_duration")
                if not count or not dur:
                    continue
                points.append(ThreadPoint(threads=n, tokens_per_s=round(count / (dur / 1e9), 2)))

        return points, _best_threads(points, cores, notes), notes

    # ---------- 4. embedding batch ----------

    async def profile_embedding_batch(
        self, sizes: tuple[int, ...] = (128, 256, 512),
    ) -> tuple[list[BatchPoint], int, list[str]]:
        """Throughput of the embedding model at different `num_batch`.

        Memory writes embed in the background while the owner is still talking.
        A batch sized past what the cores can chew blocks them long enough to
        stall the chat that is running in the foreground, which reads as the
        assistant stuttering for no visible reason.
        """
        model = settings.embedding_model
        corpus = [f"Fato de teste número {i}, com texto suficiente para medir." for i in range(24)]
        points: list[BatchPoint] = []
        notes: list[str] = []

        async with httpx.AsyncClient(base_url=self.endpoint, timeout=900.0) as c:
            for size in sizes:
                started = time.perf_counter()
                try:
                    r = await c.post("/api/embed", json={
                        "model": model, "input": corpus,
                        "options": {"num_batch": size},
                    })
                    r.raise_for_status()
                except Exception as e:  # noqa: BLE001
                    notes.append(f"num_batch={size} falhou: {str(e)[:120]}")
                    continue
                elapsed = time.perf_counter() - started
                if elapsed <= 0:
                    continue
                points.append(BatchPoint(num_batch=size, texts_per_s=round(len(corpus) / elapsed, 2)))

        best = max(points, key=lambda p: p.texts_per_s).num_batch if points else 0
        return points, best, notes

    # ---------- 5. swap cost ----------

    async def measure_swap_cost(self, models: list[str] | None = None) -> tuple[list[SwapCost], list[str]]:
        """What it costs, in seconds, to pull a model off disk into RAM.

        This is the number behind `keep_alive`. Evicting a model is free RAM and
        an expensive next request; keeping it is a fast next request and RAM the
        other models need. Neither is right in the abstract — the ratio decides,
        and on a machine that swaps, the penalty is measured in minutes.

        Each model is evicted first (`keep_alive: 0`) so the cold number really
        is cold. Without that, whatever ran last looks free.
        """
        names = models or [settings.brain_model, settings.vision_model_resolved]
        # Deduplicated: with one model doing both jobs those two entries are the
        # same name, and measuring it twice doubles the slowest probe in the
        # suite to print the same number again.
        names = list(dict.fromkeys(n for n in names if n))
        out: list[SwapCost] = []
        notes: list[str] = []

        async with httpx.AsyncClient(base_url=self.endpoint, timeout=1800.0) as c:
            for name in names:
                try:
                    # Evict, so the next call pays the real price.
                    await c.post("/api/chat", json={
                        "model": name, "messages": [], "keep_alive": 0,
                    })
                    cold, _ = await self._time_reply(c, name)
                    warm, _ = await self._time_reply(c, name)
                except Exception as e:  # noqa: BLE001
                    notes.append(f"{name}: {str(e)[:140]}")
                    continue
                out.append(SwapCost(
                    model=name,
                    cold_load_s=round(cold, 1),
                    warm_reply_s=round(warm, 1),
                    swap_penalty_s=round(max(cold - warm, 0.0), 1),
                ))

        return out, notes

    # ---------- everything, then one answer ----------

    async def full_sweep(self) -> dict:
        """Run every probe and collapse the results into env lines to set.

        Order matters: the swap measurement evicts models, so it runs LAST.
        Doing it first would make every later probe pay a cold load and report a
        machine slower than the one the owner actually has.
        """
        report = await self.probe(benchmark=False)
        ctx_points, knee, ctx_notes = await self.profile_context()
        thr_points, threads, thr_notes = await self.tune_threads()
        bat_points, batch, bat_notes = await self.profile_embedding_batch()
        swaps, swap_notes = await self.measure_swap_cost()

        env: dict[str, str] = {}
        if knee:
            env["BRAIN_NUM_CTX"] = str(knee)
        if threads:
            env["BRAIN_NUM_THREAD"] = str(threads)
        if batch:
            env["EMBEDDING_NUM_BATCH"] = str(batch)

        # keep_alive follows the measured penalty rather than a preference. A
        # model that reloads in a couple of seconds can be evicted aggressively;
        # one that takes a minute must not be, or every camera frame costs the
        # next chat message a full reload.
        for s in swaps:
            if s.model == settings.brain_model:
                env["BRAIN_KEEP_ALIVE"] = "30m" if s.swap_penalty_s > 20 else "10m"
            elif s.model == settings.vision_model_resolved:
                # Only a genuinely separate vision model may be evicted early.
                # When the eyes are the brain this branch is unreachable (the
                # test above matched first), which is the point: recommending a
                # short VISION_KEEP_ALIVE for the brain would tell the owner to
                # configure the assistant to unload itself after every photo.
                env["VISION_KEEP_ALIVE"] = "0" if s.swap_penalty_s < 20 else "2m"

        findings = list(report.findings)
        for s in swaps:
            findings.append(
                f"{s.model}: carregar do disco custa {s.swap_penalty_s}s a mais "
                f"que responder já carregado ({s.cold_load_s}s vs {s.warm_reply_s}s)."
            )

        return {
            "host": {"cores": report.host_cores, "ram_gb": round(report.host_ram_gb, 1)},
            "models": [asdict(m) for m in report.models],
            "context": {"points": [asdict(p) for p in ctx_points], "knee_tokens": knee},
            "threads": {"points": [asdict(p) for p in thr_points], "best": threads},
            "embedding_batch": {"points": [asdict(p) for p in bat_points], "best": batch},
            "swap": [asdict(s) for s in swaps],
            "findings": findings,
            "notes": ctx_notes + thr_notes + bat_notes + swap_notes,
            "env": [f"{k}={v}" for k, v in env.items()] + report.actions,
        }

    # ---------- judgement ----------

    def _analyse(self, report: Report) -> None:
        f, a = report.findings, report.actions
        chat = [m for m in report.models if "completion" in m.capabilities]
        by_speed = sorted(
            [m for m in chat if m.warm_reply_s is not None],
            key=lambda m: m.warm_reply_s,
        )

        # 1 — is the brain the fastest thing that can do the job?
        brain = next((m for m in report.models if m.name == settings.brain_model), None)
        if brain is None:
            f.append(f"BRAIN_MODEL '{settings.brain_model}' não está instalado.")
            a.append(f"ollama pull {settings.brain_model}")
        elif brain.warm_reply_s is not None:
            faster = [m for m in by_speed
                      if m.warm_reply_s < brain.warm_reply_s * 0.7 and "tools" in m.capabilities]
            if faster:
                best = faster[0]
                f.append(
                    f"{best.name} responde em {best.warm_reply_s}s contra "
                    f"{brain.warm_reply_s}s de {brain.name}, e também tem 'tools'."
                )
                a.append(f"BRAIN_MODEL={best.name}")

        # 2 — can the brain act at all?
        if brain and "tools" not in brain.capabilities:
            f.append(
                f"{brain.name} não tem 'tools': o assistente conversa mas não "
                f"consegue gravar memória, criar meta nem disparar automação."
            )
            a.append("BRAIN_MODEL=um modelo com 'tools' E 'vision' (qwen3-vl:2b)")

        # 2b — does it see, and is a second model still being paid for?
        #
        # One model is the goal, not an accident: two resident models on this
        # box evict each other, and a turn can only act on what it saw when the
        # same model did both.
        if brain and settings.vision_enabled:
            if settings.vision_shares_the_brain and "vision" not in brain.capabilities:
                f.append(
                    f"{brain.name} não tem 'vision' e VISION_MODEL está vazio: "
                    f"câmera, OCR e anexos não têm quem os leia."
                )
                a.append("BRAIN_MODEL=um modelo com 'vision' (qwen3-vl:2b)")
            elif not settings.vision_shares_the_brain and "vision" in brain.capabilities:
                eyes = next(
                    (m for m in report.models if m.name == settings.vision_model_resolved), None
                )
                gb = f", liberando {eyes.size_gb} GB" if eyes else ""
                f.append(
                    f"{brain.name} já enxerga, mas VISION_MODEL aponta para "
                    f"{settings.vision_model_resolved}: dois modelos disputam a RAM e "
                    f"nenhum turno consegue ver e agir junto."
                )
                a.append(f"VISION_MODEL= (vazio, para o próprio cérebro enxergar{gb})")

        # 3 — quantisation
        for m in chat:
            if m.quantization.upper().startswith(("F16", "F32", "Q8")):
                f.append(
                    f"{m.name} está em {m.quantization}, sem quantização agressiva. "
                    f"Uma variante Q4_K_M ocupa ~metade da RAM e roda bem mais rápido "
                    f"em CPU, com perda de qualidade pequena."
                )
                a.append(f"ollama pull {m.name.split(':')[0]}:q4_K_M")

        # 4 — memory budget, per target
        resident = sum(m.size_gb for m in report.models if m.loaded)
        for target, budget in TARGET_BUDGETS_GB.items():
            if resident > budget:
                f.append(
                    f"{resident:.1f} GB de modelos residentes excede o orçamento de "
                    f"{budget} GB do alvo '{target}'."
                )
        if len([m for m in report.models if m.loaded]) > 1:
            a.append(
                "OLLAMA_MAX_LOADED_MODELS=1 para não manter dois modelos generativos "
                "na RAM ao mesmo tempo (o de embeddings é pequeno e vive à parte)"
            )

        # 5 — threads
        if report.host_cores and report.host_cores <= 4:
            a.append(
                f"OLLAMA_NUM_PARALLEL=1 — com {report.host_cores} núcleos, atender duas "
                f"requisições ao mesmo tempo deixa as duas lentas"
            )

        # 6 — prompt cost, measured elsewhere but decided here
        if settings.tools_enabled:
            a.append(
                "TOOL_MAX_ROUNDS=2 — cada rodada é uma inferência inteira; em CPU o "
                "custo de uma quarta rodada supera o que ela costuma acrescentar"
            )

        if not f:
            f.append("Nada gritante: a configuração atual está coerente com esta máquina.")


def _knee(points: list[ContextPoint]) -> int:
    """The largest context whose per-token cost has not yet blown up.

    "Blown up" is 1.5x the cheapest rung measured. A plain "pick the biggest"
    would always return the last rung, and a plain "pick the fastest per token"
    would always return the first — neither is a decision. The knee is the last
    size that still reads at roughly the machine's best rate.
    """
    if not points:
        return 0
    floor = min(p.ms_per_token for p in points)
    ok = [p for p in points if p.ms_per_token <= floor * 1.5]
    return max(p.tokens for p in ok) if ok else points[0].tokens


def _best_threads(points: list[ThreadPoint], cores: int, notes: list[str]) -> int:
    """Fastest thread count, preferring to leave one core for the system.

    On a 4-core box the kernel is also running a web server, a database and
    possibly speech synthesis. A model that owns every core wins the benchmark
    and loses the experience, so a near-tie goes to the setting that leaves
    something for everyone else.
    """
    if not points:
        return 0
    best = max(points, key=lambda p: p.tokens_per_s)
    if cores > 1:
        spare = next((p for p in points if p.threads == cores - 1), None)
        if spare and spare.tokens_per_s >= best.tokens_per_s * 0.95:
            notes.append(
                f"{spare.threads} threads ficam a {spare.tokens_per_s / best.tokens_per_s:.0%} "
                f"de {best.threads}, e deixam um núcleo para o sistema."
            )
            return spare.threads
    return best.threads


_optimizer: Optimizer | None = None


def get_optimizer() -> Optimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = Optimizer()
    return _optimizer
