"""
Self-optimisation — the kernel measures its own inference setup.

  GET /api/v1/optimize          leitura rápida, sem benchmark
  POST /api/v1/optimize/probe   mede cada modelo (lento: carrega e gera)

It reports; it does not silently rewrite your configuration. Every action comes
back as the exact env line to set, so the owner decides what their machine does.
A tuner that edits .env behind your back is how a kernel ends up in a state
nobody can explain.
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_owner
from app.brain.optimizer import get_optimizer
from app.models.models import Owner

router = APIRouter(prefix="/api/v1/optimize", tags=["optimize"])


@router.get("")
async def inspect(owner: Owner = Depends(get_current_owner)) -> dict:
    """What is installed and configured, without running any inference."""
    return (await get_optimizer().probe(benchmark=False)).to_dict()


@router.post("/probe")
async def probe(owner: Owner = Depends(get_current_owner)) -> dict:
    """Time every chat model, cold and warm. Minutes on a CPU box — by design:
    the numbers are the point, and they cannot be obtained without paying for
    them once."""
    return (await get_optimizer().probe(benchmark=True)).to_dict()


@router.post("/context")
async def context(owner: Owner = Depends(get_current_owner)) -> dict:
    """Find the context size past which reading costs more per token."""
    points, knee, notes = await get_optimizer().profile_context()
    return {
        "points": [asdict(p) for p in points],
        "recommended_num_ctx": knee,
        "env": f"BRAIN_NUM_CTX={knee}" if knee else None,
        "notes": notes,
    }


@router.post("/threads")
async def threads(owner: Owner = Depends(get_current_owner)) -> dict:
    """Generation speed at each thread count, and the one worth using."""
    points, best, notes = await get_optimizer().tune_threads()
    return {
        "points": [asdict(p) for p in points],
        "recommended_num_thread": best,
        "env": f"BRAIN_NUM_THREAD={best}" if best else None,
        "notes": notes,
    }


@router.post("/embedding-batch")
async def embedding_batch(owner: Owner = Depends(get_current_owner)) -> dict:
    """Embedding throughput at 128 / 256 / 512."""
    points, best, notes = await get_optimizer().profile_embedding_batch()
    return {
        "points": [asdict(p) for p in points],
        "recommended_num_batch": best,
        "env": f"EMBEDDING_NUM_BATCH={best}" if best else None,
        "notes": notes,
    }


@router.post("/swap")
async def swap(owner: Owner = Depends(get_current_owner)) -> dict:
    """What a model swap costs, which is what `keep_alive` is trading against."""
    costs, notes = await get_optimizer().measure_swap_cost()
    return {"models": [asdict(c) for c in costs], "notes": notes}


@router.post("/full")
async def full(owner: Owner = Depends(get_current_owner)) -> dict:
    """Every probe, then one list of env lines to apply.

    Slow — this occupies the machine it is measuring, for several minutes. It
    returns settings to set; it does not write them. The owner's .env stays the
    owner's.
    """
    return await get_optimizer().full_sweep()
