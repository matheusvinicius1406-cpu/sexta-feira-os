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
