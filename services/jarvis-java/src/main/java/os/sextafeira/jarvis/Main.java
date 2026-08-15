package os.sextafeira.jarvis;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;

/**
 * Jarvis Java Service — the JVM worker that does what the Python kernel is
 * slow at, talking to it over its own HTTP API.
 *
 * v0.1 — two real capabilities:
 *
 *   GET  /health                       self status + live ping to the Python
 *                                      kernel (the Python <-> Java link, proven
 *                                      every request)
 *   POST /api/v1/audio/waveform        download audio (URL), decode to WAV,
 *                                      compute per-second RMS peaks — a JVM
 *                                      strength (byte processing, threads)
 *                                      that the HUD can render later
 *
 * The kernel stays the source of truth; this service never invents state. It
 * only processes what it is handed and reports what it measured.
 */
public final class Main {

    public static void main(String[] args) {
        int port = Integer.parseInt(System.getenv().getOrDefault("JARVIS_JAVA_PORT", "17494"));
        String kernelUrl = System.getenv().getOrDefault("KERNEL_URL", "http://127.0.0.1:8000");

        Javalin app = Javalin.create(cfg -> {
            cfg.showJavalinBanner = false;
            cfg.http.maxRequestSize = 8_388_608L; // 8 MB body cap
        });

        app.get("/health", ctx -> ctx.json(Health.check(kernelUrl)));
        app.post("/api/v1/audio/waveform", ctx -> {
            WaveformRequest req = new ObjectMapper().readValue(ctx.body(), WaveformRequest.class);
            if (req.url() == null || req.url().isBlank()) {
                ctx.status(400).json(java.util.Map.of("error", "url obrigatória"));
                return;
            }
            try {
                ctx.json(AudioWaveform.compute(req.url(), req.maxSeconds()));
            } catch (IllegalArgumentException e) {
                ctx.status(400).json(java.util.Map.of("error", e.getMessage()));
            } catch (Exception e) {
                ctx.status(502).json(java.util.Map.of("error", "falha ao processar áudio: " + e.getMessage()));
            }
        });

        app.start(port);
        System.out.println("jarvis-java no ar em :" + port + " (kernel em " + kernelUrl + ")");
    }
}
