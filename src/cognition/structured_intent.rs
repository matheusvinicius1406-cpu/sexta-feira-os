use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub struct StructuredIntent {
    pub intent_id: String,
    pub timestamp_ns: u64,
    pub source: IntentSource,
    pub confidence: f32,
    pub requested_tool: String,
    pub parameters: HashMap<String, String>,
    pub reasoning_trace_hash: u64,
    pub capability_requirements: Vec<String>,
    pub schema_version: u8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IntentSource {
    HumanVoice,
    ScreenGesture,
    ApplicationRequest,
    SystemTrigger,
    MemoryRecall,
}

impl StructuredIntent {
    pub fn new(
        intent_id: String,
        requested_tool: String,
        source: IntentSource,
    ) -> Self {
        Self {
            intent_id,
            timestamp_ns: current_time_ns(),
            source,
            confidence: 1.0,
            requested_tool,
            parameters: HashMap::new(),
            reasoning_trace_hash: 0,
            capability_requirements: Vec::new(),
            schema_version: 1,
        }
    }

    pub fn with_confidence(mut self, confidence: f32) -> Self {
        self.confidence = confidence.clamp(0.0, 1.0);
        self
    }

    pub fn with_parameter(mut self, key: String, value: String) -> Self {
        self.parameters.insert(key, value);
        self
    }

    pub fn with_capability(mut self, cap: String) -> Self {
        self.capability_requirements.push(cap);
        self
    }

    pub fn set_reasoning_trace(&mut self, hash: u64) {
        self.reasoning_trace_hash = hash;
    }

    pub fn is_valid(&self) -> bool {
        !self.intent_id.is_empty()
            && !self.requested_tool.is_empty()
            && self.confidence > 0.0
            && self.schema_version <= 1
    }

    pub fn compute_intent_hash(&self) -> u64 {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        hash ^= fnv_hash_str(&self.intent_id);
        hash = hash.wrapping_mul(PRIME);

        hash ^= fnv_hash_str(&self.requested_tool);
        hash = hash.wrapping_mul(PRIME);

        hash
    }

    pub fn age_ms(&self) -> u64 {
        let now_ns = current_time_ns();
        if now_ns > self.timestamp_ns {
            (now_ns - self.timestamp_ns) / 1_000_000
        } else {
            0
        }
    }
}

#[inline]
fn fnv_hash_str(s: &str) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    const PRIME: u64 = 0x100000001b3;

    for byte in s.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(PRIME);
    }

    hash
}

#[inline]
fn current_time_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_structured_intent_creation() {
        let intent = StructuredIntent::new(
            "intent-001".to_string(),
            "file_search".to_string(),
            IntentSource::HumanVoice,
        );

        assert!(intent.is_valid());
        assert_eq!(intent.confidence, 1.0);
    }

    #[test]
    fn test_structured_intent_builder() {
        let intent = StructuredIntent::new(
            "intent-002".to_string(),
            "search".to_string(),
            IntentSource::ScreenGesture,
        )
        .with_confidence(0.85)
        .with_parameter("query".to_string(), "rust".to_string())
        .with_capability("file_access".to_string());

        assert_eq!(intent.confidence, 0.85);
        assert_eq!(intent.parameters.get("query"), Some(&"rust".to_string()));
        assert_eq!(intent.capability_requirements.len(), 1);
    }

    #[test]
    fn test_intent_hash_deterministic() {
        let intent1 = StructuredIntent::new(
            "same".to_string(),
            "tool".to_string(),
            IntentSource::HumanVoice,
        );

        let intent2 = StructuredIntent::new(
            "same".to_string(),
            "tool".to_string(),
            IntentSource::HumanVoice,
        );

        assert_eq!(intent1.compute_intent_hash(), intent2.compute_intent_hash());
    }

    #[test]
    fn test_intent_validation() {
        let valid = StructuredIntent::new(
            "test".to_string(),
            "tool".to_string(),
            IntentSource::HumanVoice,
        );

        assert!(valid.is_valid());

        let mut invalid = valid.clone();
        invalid.intent_id = String::new();
        assert!(!invalid.is_valid());
    }
}
