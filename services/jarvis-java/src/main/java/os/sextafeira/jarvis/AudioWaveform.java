package os.sextafeira.jarvis;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;

/**
 * Audio waveform peaks, computed in the JVM — the kind of byte/thread work
 * Python does slowly and Java does comfortably. The kernel hands us a URL; we
 * download a bounded slice, decode to PCM WAV (ffmpeg when the format is not
 * WAV already), and return per-second RMS peaks in 0..1.
 */
final class AudioWaveform {

    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();

    private static final int MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024; // 40 MB safety cap

    private AudioWaveform() {}

    static Map<String, Object> compute(String url, int maxSeconds) throws Exception {
        byte[] raw = download(url);
        byte[] wav = toWav(raw);
        float[] peaks = peaksPerSecond(wav, maxSeconds);
        return Map.of(
                "peaks", peaks,
                "duration_s", peaks.length,
                "source", url,
                "bytes", raw.length
        );
    }

    /** For tests: peaks straight from an in-memory WAV (no network, no ffmpeg). */
    static Map<String, Object> computeFromWav(byte[] wav, int maxSeconds) throws Exception {
        float[] peaks = peaksPerSecond(wav, maxSeconds);
        return Map.of("peaks", peaks, "duration_s", peaks.length, "bytes", wav.length);
    }

    private static byte[] download(String url) throws Exception {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(60))
                .GET()
                .header("User-Agent", "jarvis-java/0.1")
                .build();
        HttpResponse<byte[]> res = CLIENT.send(req, HttpResponse.BodyHandlers.ofByteArray());
        if (res.statusCode() != 200) {
            throw new IllegalArgumentException("download falhou: HTTP " + res.statusCode());
        }
        if (res.body().length > MAX_DOWNLOAD_BYTES) {
            throw new IllegalArgumentException("áudio grande demais (" + res.body().length + " bytes)");
        }
        return res.body();
    }

    /** Normalize any audio to 24 kHz mono s16 WAV via ffmpeg (already a kernel dependency). */
    private static byte[] toWav(byte[] raw) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
                "-f", "wav", "pipe:1"
        );
        pb.redirectErrorStream(true);
        Process p = pb.start();
        // Deadlock clássico de pipe: escrever 9 MB no stdin enquanto o stdout
        // (buffer de 64 KB) enche bloqueia o filho — e nós bloqueamos esperando
        // o filho. Drena o stdout numa thread enquanto o main escreve o stdin.
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        Thread drain = new Thread(() -> {
            byte[] buf = new byte[8192];
            try {
                int n;
                while ((n = p.getInputStream().read(buf)) > 0) {
                    out.write(buf, 0, n);
                }
            } catch (Exception ignored) {
                Thread.currentThread().interrupt();
            }
        });
        drain.start();
        p.getOutputStream().write(raw);
        p.getOutputStream().close();
        drain.join();
        int code = p.waitFor();
        if (code != 0 || out.size() < 44) {
            throw new IllegalArgumentException("ffmpeg falhou (code " + code + ") — formato não suportado");
        }
        return out.toByteArray();
    }

    private static float[] peaksPerSecond(byte[] wav, int maxSeconds) throws Exception {
        try (AudioInputStream in = AudioSystem.getAudioInputStream(new ByteArrayInputStream(wav))) {
            AudioFormat fmt = in.getFormat();
            int frameSize = fmt.getFrameSize();
            int sampleRate = (int) fmt.getSampleRate();
            int perSecond = sampleRate * frameSize; // bytes per second (mono s16 => 2 * rate)

            int totalSeconds = Math.min((int) (wav.length / perSecond), maxSeconds);
            if (totalSeconds < 1) {
                throw new IllegalArgumentException("áudio curto demais para waveform");
            }
            float[] peaks = new float[totalSeconds];
            byte[] chunk = new byte[perSecond];
            for (int s = 0; s < totalSeconds; s++) {
                int read = in.readNBytes(chunk, 0, chunk.length);
                peaks[s] = rms(chunk, read);
            }
            return peaks;
        }
    }

    /** RMS of signed 16-bit little-endian samples, normalized to 0..1 (reference 32768). */
    private static float rms(byte[] pcm, int len) {
        long sum = 0;
        int count = 0;
        for (int i = 0; i + 1 < len; i += 2) {
            int sample = (pcm[i] & 0xFF) | (pcm[i + 1] << 8);
            sum += (long) sample * sample;
            count++;
        }
        if (count == 0) return 0f;
        double rms = Math.sqrt((double) sum / count) / 32768.0;
        return (float) Math.min(1.0, rms);
    }
}
