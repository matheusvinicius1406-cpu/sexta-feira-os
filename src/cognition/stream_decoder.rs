use crate::cognition::cognitive_errors::{CognitiveError, CognitiveResult};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StreamState {
    Idle,
    Active,
    Corrupted,
    Complete,
}

pub struct DecoderMetrics {
    pub chunks_received: Arc<AtomicU64>,
    pub bytes_received: Arc<AtomicU64>,
    pub json_errors: Arc<AtomicU64>,
    pub valid_intents: Arc<AtomicU64>,
}

impl DecoderMetrics {
    pub fn new() -> Self {
        Self {
            chunks_received: Arc::new(AtomicU64::new(0)),
            bytes_received: Arc::new(AtomicU64::new(0)),
            json_errors: Arc::new(AtomicU64::new(0)),
            valid_intents: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn record_chunk(&self, size: u64) {
        self.chunks_received.fetch_add(1, Ordering::Relaxed);
        self.bytes_received.fetch_add(size, Ordering::Relaxed);
    }

    pub fn record_error(&self) {
        self.json_errors.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_valid_intent(&self) {
        self.valid_intents.fetch_add(1, Ordering::Relaxed);
    }

    pub fn get_chunks_received(&self) -> u64 {
        self.chunks_received.load(Ordering::Acquire)
    }

    pub fn get_bytes_received(&self) -> u64 {
        self.bytes_received.load(Ordering::Acquire)
    }

    pub fn get_json_errors(&self) -> u64 {
        self.json_errors.load(Ordering::Acquire)
    }

    pub fn get_valid_intents(&self) -> u64 {
        self.valid_intents.load(Ordering::Acquire)
    }
}

impl Default for DecoderMetrics {
    fn default() -> Self {
        Self::new()
    }
}

pub struct StreamDecoder {
    state: StreamState,
    buffer: String,
    metrics: DecoderMetrics,
    max_buffer_size: usize,
    corrupted_reason: Option<String>,
}

impl StreamDecoder {
    pub fn new(max_buffer_size: usize) -> Self {
        Self {
            state: StreamState::Idle,
            buffer: String::with_capacity(4096),
            metrics: DecoderMetrics::new(),
            max_buffer_size,
            corrupted_reason: None,
        }
    }

    pub fn process_chunk(&mut self, chunk: &str) -> CognitiveResult<Option<String>> {
        if self.state == StreamState::Corrupted {
            return Err(CognitiveError::StreamCorruption(
                self.corrupted_reason
                    .clone()
                    .unwrap_or_else(|| "Unknown corruption".to_string()),
            ));
        }

        if chunk.is_empty() {
            return Ok(None);
        }

        if self.buffer.len() + chunk.len() > self.max_buffer_size {
            self.state = StreamState::Corrupted;
            self.corrupted_reason = Some("Buffer overflow".to_string());
            return Err(CognitiveError::StreamCorruption(
                "Buffer overflow".to_string(),
            ));
        }

        self.buffer.push_str(chunk);
        self.metrics.record_chunk(chunk.len() as u64);
        self.state = StreamState::Active;

        if self.is_complete_intent_chunk(&self.buffer) {
            let result = self.buffer.clone();
            self.reset_buffer();
            self.state = StreamState::Complete;
            self.metrics.record_valid_intent();
            Ok(Some(result))
        } else {
            Ok(None)
        }
    }

    pub fn try_flush(&mut self) -> CognitiveResult<Option<String>> {
        if self.buffer.is_empty() {
            self.state = StreamState::Idle;
            return Ok(None);
        }

        if !self.is_potentially_valid(&self.buffer) {
            self.state = StreamState::Corrupted;
            self.corrupted_reason = Some("Invalid intent format".to_string());
            return Err(CognitiveError::StreamCorruption(
                "Invalid intent format".to_string(),
            ));
        }

        let result = self.buffer.clone();
        self.reset_buffer();
        self.state = StreamState::Complete;
        self.metrics.record_valid_intent();
        Ok(Some(result))
    }

    pub fn reset(&mut self) {
        self.reset_buffer();
        self.state = StreamState::Idle;
        self.corrupted_reason = None;
    }

    pub fn abort_invalid_stream(&mut self, reason: String) {
        self.state = StreamState::Corrupted;
        self.corrupted_reason = Some(reason);
        self.reset_buffer();
    }

    pub fn current_state(&self) -> StreamState {
        self.state
    }

    pub fn metrics(&self) -> &DecoderMetrics {
        &self.metrics
    }

    fn reset_buffer(&mut self) {
        self.buffer.clear();
    }

    fn is_complete_intent_chunk(&self, text: &str) -> bool {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            return false;
        }

        // An intent is complete when it has at least the three required fields:
        // intent_id, tool, source. We can detect this by looking for their
        // markers at the start of lines (key:value format, not JSON).
        let mut has_id = false;
        let mut has_tool = false;
        let mut has_source = false;

        for line in trimmed.lines() {
            let line = line.trim();
            if line.starts_with("intent_id:") {
                has_id = true;
            } else if line.starts_with("tool:") {
                has_tool = true;
            } else if line.starts_with("source:") {
                has_source = true;
            }
        }

        has_id && has_tool && has_source
    }

    fn is_potentially_valid(&self, text: &str) -> bool {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            return false;
        }

        // Check that lines look like valid key:value pairs.
        let mut has_key_value = false;
        for line in trimmed.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            if line.contains(':') {
                has_key_value = true;
            } else {
                return false;  // line without colon is invalid
            }
        }

        has_key_value
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stream_decoder_creation() {
        let decoder = StreamDecoder::new(10000);
        assert_eq!(decoder.current_state(), StreamState::Idle);
    }

    #[test]
    fn test_process_valid_chunk() {
        let mut decoder = StreamDecoder::new(10000);
        // The decoder parses a line-based key:value format (not JSON) and needs
        // the three required fields: intent_id, tool, source.
        let chunk = "intent_id: test\ntool: search\nsource: voice\n";

        let result = decoder.process_chunk(chunk).unwrap();
        assert!(result.is_some());
        assert_eq!(decoder.current_state(), StreamState::Complete);
    }

    #[test]
    fn test_buffer_overflow() {
        let mut decoder = StreamDecoder::new(10);
        let chunk = "x".repeat(20);

        let result = decoder.process_chunk(&chunk);
        assert!(result.is_err());
        assert_eq!(decoder.current_state(), StreamState::Corrupted);
    }

    #[test]
    fn test_metrics_recording() {
        let mut decoder = StreamDecoder::new(10000);
        let chunk = r#"{"test": "value"}"#;

        let _ = decoder.process_chunk(chunk);
        assert_eq!(decoder.metrics().get_chunks_received(), 1);
        assert!(decoder.metrics().get_bytes_received() > 0);
    }

    #[test]
    fn test_reset() {
        let mut decoder = StreamDecoder::new(10000);
        decoder.abort_invalid_stream("test error".to_string());

        assert_eq!(decoder.current_state(), StreamState::Corrupted);

        decoder.reset();
        assert_eq!(decoder.current_state(), StreamState::Idle);
    }
}
