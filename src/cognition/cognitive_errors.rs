use std::fmt;

#[derive(Debug, Clone)]
pub enum CognitiveError {
    InvalidIntent(String),
    StreamCorruption(String),
    CapabilityViolation(String),
    SchedulerTimeout,
    BudgetExceeded(String),
    UnsafeToolProposal(String),
    ContextOverflow,
    CognitivePanic(String),
    ParseError(String),
    RegistryError(String),
    ToolNotFound(String),
    InvalidPayload(String),
}

impl fmt::Display for CognitiveError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidIntent(msg) => write!(f, "Invalid intent: {}", msg),
            Self::StreamCorruption(msg) => write!(f, "Stream corruption: {}", msg),
            Self::CapabilityViolation(msg) => write!(f, "Capability violation: {}", msg),
            Self::SchedulerTimeout => write!(f, "Scheduler timeout"),
            Self::BudgetExceeded(msg) => write!(f, "Budget exceeded: {}", msg),
            Self::UnsafeToolProposal(msg) => write!(f, "Unsafe tool proposal: {}", msg),
            Self::ContextOverflow => write!(f, "Context overflow"),
            Self::CognitivePanic(msg) => write!(f, "Cognitive panic: {}", msg),
            Self::ParseError(msg) => write!(f, "Parse error: {}", msg),
            Self::RegistryError(msg) => write!(f, "Registry error: {}", msg),
            Self::ToolNotFound(msg) => write!(f, "Tool not found: {}", msg),
            Self::InvalidPayload(msg) => write!(f, "Invalid payload: {}", msg),
        }
    }
}

impl std::error::Error for CognitiveError {}

pub type CognitiveResult<T> = Result<T, CognitiveError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_invalid_intent_error() {
        let err = CognitiveError::InvalidIntent("missing fields".to_string());
        assert_eq!(err.to_string(), "Invalid intent: missing fields");
    }

    #[test]
    fn test_stream_corruption_error() {
        let err = CognitiveError::StreamCorruption("buffer overflow".to_string());
        assert_eq!(err.to_string(), "Stream corruption: buffer overflow");
    }

    #[test]
    fn test_capability_violation_error() {
        let err = CognitiveError::CapabilityViolation("no file access".to_string());
        assert_eq!(err.to_string(), "Capability violation: no file access");
    }

    #[test]
    fn test_scheduler_timeout_error() {
        let err = CognitiveError::SchedulerTimeout;
        assert_eq!(err.to_string(), "Scheduler timeout");
    }

    #[test]
    fn test_budget_exceeded_error() {
        let err = CognitiveError::BudgetExceeded("memory limit".to_string());
        assert_eq!(err.to_string(), "Budget exceeded: memory limit");
    }

    #[test]
    fn test_unsafe_tool_proposal_error() {
        let err = CognitiveError::UnsafeToolProposal("rm -rf /".to_string());
        assert_eq!(err.to_string(), "Unsafe tool proposal: rm -rf /");
    }

    #[test]
    fn test_context_overflow_error() {
        let err = CognitiveError::ContextOverflow;
        assert_eq!(err.to_string(), "Context overflow");
    }

    #[test]
    fn test_cognitive_panic_error() {
        let err = CognitiveError::CognitivePanic("stack overflow".to_string());
        assert_eq!(err.to_string(), "Cognitive panic: stack overflow");
    }

    #[test]
    fn test_parse_error() {
        let err = CognitiveError::ParseError("invalid syntax".to_string());
        assert_eq!(err.to_string(), "Parse error: invalid syntax");
    }

    #[test]
    fn test_registry_error() {
        let err = CognitiveError::RegistryError("duplicate entry".to_string());
        assert_eq!(err.to_string(), "Registry error: duplicate entry");
    }

    #[test]
    fn test_tool_not_found_error() {
        let err = CognitiveError::ToolNotFound("search_tool".to_string());
        assert_eq!(err.to_string(), "Tool not found: search_tool");
    }

    #[test]
    fn test_invalid_payload_error() {
        let err = CognitiveError::InvalidPayload("too large".to_string());
        assert_eq!(err.to_string(), "Invalid payload: too large");
    }

    #[test]
    fn test_error_implements_std_error() {
        let err = CognitiveError::SchedulerTimeout;
        let std_err: &dyn std::error::Error = &err;
        assert_eq!(std_err.to_string(), "Scheduler timeout");
    }

    #[test]
    fn test_result_type_aliases() {
        let ok: CognitiveResult<i32> = Ok(42);
        assert_eq!(ok.unwrap(), 42);

        let err: CognitiveResult<i32> = Err(CognitiveError::ContextOverflow);
        assert!(err.is_err());
    }

    #[test]
    fn test_different_error_types_are_not_equal() {
        let a = CognitiveError::InvalidIntent("x".to_string());
        let b = CognitiveError::StreamCorruption("x".to_string());
        assert_ne!(format!("{:?}", a), format!("{:?}", b));
    }
}
