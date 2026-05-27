use crate::cognition::cognitive_errors::{CognitiveError, CognitiveResult};
use crate::cognition::structured_intent::{IntentSource, StructuredIntent};
use std::collections::HashMap;

const MAX_PAYLOAD_SIZE: usize = 1_024 * 100;
const MAX_INTENT_ID_LEN: usize = 256;
const MAX_TOOL_NAME_LEN: usize = 256;

pub struct IntentParser;

impl IntentParser {
    pub fn parse_complete_intent(payload: &str) -> CognitiveResult<StructuredIntent> {
        if payload.len() > MAX_PAYLOAD_SIZE {
            return Err(CognitiveError::InvalidPayload(
                "Payload exceeds size limit".to_string(),
            ));
        }

        if !Self::validate_schema(payload) {
            return Err(CognitiveError::InvalidIntent(
                "Schema validation failed".to_string(),
            ));
        }

        Self::parse_fields(payload)
    }

    pub fn validate_schema(payload: &str) -> bool {
        let mut has_id = false;
        let mut has_tool = false;
        let mut has_source = false;

        for line in payload.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("intent_id:") {
                has_id = true;
            }
            if trimmed.starts_with("tool:") {
                has_tool = true;
            }
            if trimmed.starts_with("source:") {
                has_source = true;
            }
        }

        has_id && has_tool && has_source
    }

    pub fn parse_partial_chunk(chunk: &str) -> CognitiveResult<Option<Vec<(String, String)>>> {
        if chunk.is_empty() {
            return Ok(None);
        }

        if chunk.len() > MAX_PAYLOAD_SIZE {
            return Err(CognitiveError::StreamCorruption(
                "Chunk exceeds size limit".to_string(),
            ));
        }

        let mut pairs = Vec::new();

        for line in chunk.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            if let Some(colon_pos) = trimmed.find(':') {
                let key = trimmed[..colon_pos].trim();
                let value = trimmed[colon_pos + 1..].trim();

                if !key.is_empty() && !value.is_empty() {
                    pairs.push((key.to_string(), value.to_string()));
                }
            }
        }

        if pairs.is_empty() {
            Ok(None)
        } else {
            Ok(Some(pairs))
        }
    }

    fn parse_fields(payload: &str) -> CognitiveResult<StructuredIntent> {
        let mut intent_id = String::new();
        let mut tool_name = String::new();
        let mut source = IntentSource::SystemTrigger;
        let mut confidence = 1.0f32;
        let mut parameters = HashMap::new();
        let mut capabilities = Vec::new();

        for line in payload.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            if let Some(colon_pos) = trimmed.find(':') {
                let key = trimmed[..colon_pos].trim();
                let value = trimmed[colon_pos + 1..].trim();

                match key {
                    "intent_id" => {
                        if value.len() > MAX_INTENT_ID_LEN {
                            return Err(CognitiveError::InvalidIntent(
                                "Intent ID too long".to_string(),
                            ));
                        }
                        intent_id = value.to_string();
                    }
                    "tool" => {
                        if value.len() > MAX_TOOL_NAME_LEN {
                            return Err(CognitiveError::InvalidIntent(
                                "Tool name too long".to_string(),
                            ));
                        }
                        tool_name = value.to_string();
                    }
                    "source" => {
                        source = Self::parse_source(value)?;
                    }
                    "confidence" => {
                        confidence = value
                            .parse::<f32>()
                            .map_err(|_| {
                                CognitiveError::ParseError("Invalid confidence value".to_string())
                            })?
                            .clamp(0.0, 1.0);
                    }
                    "param" => {
                        if let Some(eq_pos) = value.find('=') {
                            let pkey = value[..eq_pos].trim();
                            let pval = value[eq_pos + 1..].trim();
                            parameters.insert(pkey.to_string(), pval.to_string());
                        }
                    }
                    "capability" => {
                        capabilities.push(value.to_string());
                    }
                    _ => {}
                }
            }
        }

        if intent_id.is_empty() || tool_name.is_empty() {
            return Err(CognitiveError::InvalidIntent(
                "Missing required fields".to_string(),
            ));
        }

        Ok(StructuredIntent {
            intent_id,
            timestamp_ns: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos() as u64,
            source,
            confidence,
            requested_tool: tool_name,
            parameters,
            reasoning_trace_hash: 0,
            capability_requirements: capabilities,
            schema_version: 1,
        })
    }

    fn parse_source(source_str: &str) -> CognitiveResult<IntentSource> {
        match source_str.trim().to_lowercase().as_str() {
            "voice" | "human_voice" => Ok(IntentSource::HumanVoice),
            "gesture" | "screen_gesture" => Ok(IntentSource::ScreenGesture),
            "app" | "application" => Ok(IntentSource::ApplicationRequest),
            "system" => Ok(IntentSource::SystemTrigger),
            "memory" => Ok(IntentSource::MemoryRecall),
            _ => Err(CognitiveError::ParseError(format!(
                "Unknown source: {}",
                source_str
            ))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_complete_intent() {
        let payload = r#"
intent_id: task-001
tool: file_search
source: voice
confidence: 0.95
param: query=rust
capability: file_access
        "#;

        let intent = IntentParser::parse_complete_intent(payload).unwrap();
        assert_eq!(intent.intent_id, "task-001");
        assert_eq!(intent.requested_tool, "file_search");
        assert_eq!(intent.source, IntentSource::HumanVoice);
        assert_eq!(intent.confidence, 0.95);
    }

    #[test]
    fn test_validate_schema() {
        let valid = "intent_id: x\ntool: y\nsource: voice";
        let invalid = "intent_id: x\ntool: y";

        assert!(IntentParser::validate_schema(valid));
        assert!(!IntentParser::validate_schema(invalid));
    }

    #[test]
    fn test_parse_partial_chunk() {
        let chunk = "intent_id: test\ntool: search";
        let pairs = IntentParser::parse_partial_chunk(chunk).unwrap();

        assert!(pairs.is_some());
        let p = pairs.unwrap();
        assert_eq!(p.len(), 2);
    }

    #[test]
    fn test_payload_size_limit() {
        let oversized = "x".repeat(MAX_PAYLOAD_SIZE + 1);
        let result = IntentParser::parse_complete_intent(&oversized);

        assert!(result.is_err());
    }

    #[test]
    fn test_missing_required_fields() {
        let payload = "intent_id: test";
        let result = IntentParser::parse_complete_intent(payload);

        assert!(result.is_err());
    }
}
