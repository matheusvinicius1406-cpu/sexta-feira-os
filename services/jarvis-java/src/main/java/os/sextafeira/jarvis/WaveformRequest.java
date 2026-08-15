package os.sextafeira.jarvis;

import com.fasterxml.jackson.annotation.JsonProperty;

record WaveformRequest(
        String url,
        @JsonProperty("max_seconds") Integer maxSeconds
) {
    int capSeconds() {
        return maxSeconds == null ? 60 : Math.min(Math.max(maxSeconds, 1), 300);
    }
}
