package os.sextafeira.jarvis;

import org.junit.jupiter.api.Test;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioFileFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Waveform from an in-memory sine WAV — no network, no ffmpeg. The shape is
 * the contract: N seconds in, N peaks out, louder sections peak higher.
 */
class AudioWaveformTest {

    private static final int RATE = 24000;

    /** Raw signed 16-bit LE PCM, `seconds` long, sine at 440 Hz with `amplitude`. */
    private static byte[] sinePcm(int seconds, int amplitude) {
        int frames = RATE * seconds;
        byte[] pcm = new byte[frames * 2];
        double freq = 440.0;
        for (int i = 0; i < frames; i++) {
            short sample = (short) (amplitude * Math.sin(2 * Math.PI * freq * i / RATE));
            pcm[i * 2] = (byte) (sample & 0xFF);
            pcm[i * 2 + 1] = (byte) ((sample >> 8) & 0xFF);
        }
        return pcm;
    }

    /** Wrap raw PCM in a real WAV container (AudioSystem.write). */
    private static byte[] wavFromPcm(byte[] pcm) throws Exception {
        AudioFormat fmt = new AudioFormat(RATE, 16, 1, true, false);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        AudioSystem.write(
                new AudioInputStream(new ByteArrayInputStream(pcm), fmt, pcm.length / 2),
                AudioFileFormat.Type.WAVE, out);
        return out.toByteArray();
    }

    @Test
    void threeSecondsIn_threePeaksOut() throws Exception {
        Map<String, Object> r = AudioWaveform.computeFromWav(wavFromPcm(sinePcm(3, 16000)), 60);
        float[] peaks = (float[]) r.get("peaks");
        assertEquals(3, peaks.length);
        assertTrue(peaks[0] > 0.3f, "tom de 16k deve dar pico alto, veio " + peaks[0]);
    }

    @Test
    void louderSectionsPeakHigher() throws Exception {
        // 2s quiet + 2s loud — same frequency, real WAV container around both.
        byte[] pcm = new byte[sinePcm(2, 4000).length + sinePcm(2, 30000).length];
        System.arraycopy(sinePcm(2, 4000), 0, pcm, 0, sinePcm(2, 4000).length);
        System.arraycopy(sinePcm(2, 30000), 0, pcm, sinePcm(2, 4000).length, sinePcm(2, 30000).length);

        Map<String, Object> r = AudioWaveform.computeFromWav(wavFromPcm(pcm), 60);
        float[] peaks = (float[]) r.get("peaks");
        assertEquals(4, peaks.length);
        assertTrue(peaks[3] > peaks[0], "seção alta deve pico maior: " + peaks[0] + " vs " + peaks[3]);
    }

    @Test
    void maxSecondsCapsThePeaks() throws Exception {
        Map<String, Object> r = AudioWaveform.computeFromWav(wavFromPcm(sinePcm(10, 8000)), 3);
        assertEquals(3, ((float[]) r.get("peaks")).length);
    }
}
