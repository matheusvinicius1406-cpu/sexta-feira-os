package os.sextafeira.jarvis;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

/** Self status plus a live ping to the Python kernel — the Java<->Python link. */
final class Health {

    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .build();

    private Health() {}

    static Map<String, Object> check(String kernelUrl) {
        long started = System.nanoTime();
        boolean ok = false;
        long latencyMs = -1;
        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(kernelUrl + "/api/v1/health"))
                    .timeout(Duration.ofSeconds(5))
                    .GET()
                    .build();
            HttpResponse<String> res = CLIENT.send(req, HttpResponse.BodyHandlers.ofString());
            ok = res.statusCode() == 200;
            latencyMs = (System.nanoTime() - started) / 1_000_000;
        } catch (Exception e) {
            latencyMs = (System.nanoTime() - started) / 1_000_000;
        }
        return Map.of(
                "service", "jarvis-java",
                "version", "0.1.0",
                "uptime_s", (System.currentTimeMillis() - Boot.startedAt) / 1000,
                "kernel", Map.of("ok", ok, "latency_ms", latencyMs, "url", kernelUrl)
        );
    }
}
