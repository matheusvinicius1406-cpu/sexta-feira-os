use crate::cognition::{CognitiveScheduler, StructuredIntent, ToolRegistry};
use crate::integration::secure_intent::{CapabilityMatrix, SecureIntent};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

pub type BridgeResult<T> = Result<T, BridgeError>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BridgeError {
    IntentValidationFailed(String),
    CapabilityCheckFailed(String),
    SchedulerDecisionDenied(String),
    SchemaTransformFailed(String),
    TimeoutEnforced,
    CancellationRequested,
}

impl std::fmt::Display for BridgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BridgeError::IntentValidationFailed(msg) => {
                write!(f, "Intent validation failed: {}", msg)
            }
            BridgeError::CapabilityCheckFailed(msg) => {
                write!(f, "Capability check failed: {}", msg)
            }
            BridgeError::SchedulerDecisionDenied(msg) => write!(f, "Scheduler denied: {}", msg),
            BridgeError::SchemaTransformFailed(msg) => {
                write!(f, "Schema transform failed: {}", msg)
            }
            BridgeError::TimeoutEnforced => write!(f, "Timeout enforced"),
            BridgeError::CancellationRequested => write!(f, "Cancellation requested"),
        }
    }
}

pub struct ExecutionRequest {
    pub secure_intent: SecureIntent,
    pub deadline_ns: u64,
}

impl ExecutionRequest {
    pub fn new(secure_intent: SecureIntent) -> Self {
        let deadline_ns = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64
            + (30_000_000_000u64);

        Self {
            secure_intent,
            deadline_ns,
        }
    }

    pub fn with_timeout_ms(mut self, ms: u64) -> Self {
        self.deadline_ns = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64
            + (ms * 1_000_000u64);
        self
    }

    pub fn is_expired(&self) -> bool {
        let now_ns = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        now_ns > self.deadline_ns
    }

    pub fn time_remaining_ms(&self) -> i64 {
        let now_ns = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        if now_ns >= self.deadline_ns {
            0
        } else {
            ((self.deadline_ns - now_ns) / 1_000_000) as i64
        }
    }
}

pub struct ExecutionContext {
    pub request_id: String,
    pub cognitive_intent: StructuredIntent,
    pub secure_intent: SecureIntent,
}

pub struct CognitiveRuntimeBridge {
    scheduler: CognitiveScheduler,
    registry: ToolRegistry,
    capability_matrix: CapabilityMatrix,
    intents_processed: Arc<AtomicU64>,
    intents_rejected: Arc<AtomicU64>,
    timeouts_enforced: Arc<AtomicU64>,
}

impl CognitiveRuntimeBridge {
    pub fn new(
        scheduler: CognitiveScheduler,
        registry: ToolRegistry,
        capability_matrix: CapabilityMatrix,
    ) -> Self {
        Self {
            scheduler,
            registry,
            capability_matrix,
            intents_processed: Arc::new(AtomicU64::new(0)),
            intents_rejected: Arc::new(AtomicU64::new(0)),
            timeouts_enforced: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn process_execution_request(
        &self,
        request: ExecutionRequest,
    ) -> BridgeResult<ExecutionContext> {
        if request.is_expired() {
            self.timeouts_enforced.fetch_add(1, Ordering::Relaxed);
            return Err(BridgeError::TimeoutEnforced);
        }

        request.secure_intent.validate_all().map_err(|e| {
            self.intents_rejected.fetch_add(1, Ordering::Relaxed);
            BridgeError::IntentValidationFailed(e.to_string())
        })?;

        self.capability_matrix
            .validate_intent(&request.secure_intent.source, &request.secure_intent)
            .map_err(|e| {
                self.intents_rejected.fetch_add(1, Ordering::Relaxed);
                BridgeError::CapabilityCheckFailed(e.to_string())
            })?;

        let permit = self.scheduler.request_execution().map_err(|e| {
            self.intents_rejected.fetch_add(1, Ordering::Relaxed);
            BridgeError::SchedulerDecisionDenied(format!("{:?}", e))
        })?;

        self.scheduler
            .enforce_execution_limits(&permit)
            .map_err(|e| {
                self.intents_rejected.fetch_add(1, Ordering::Relaxed);
                BridgeError::SchedulerDecisionDenied(format!("{:?}", e))
            })?;

        let cognitive_intent = StructuredIntent::new(
            request.secure_intent.id.clone(),
            request.secure_intent.action.clone(),
            crate::cognition::IntentSource::SystemTrigger,
        );

        if !self.registry.tool_exists(&cognitive_intent.requested_tool) {
            self.intents_rejected.fetch_add(1, Ordering::Relaxed);
            return Err(BridgeError::SchemaTransformFailed(
                "Tool not registered".to_string(),
            ));
        }

        self.intents_processed.fetch_add(1, Ordering::Relaxed);

        Ok(ExecutionContext {
            request_id: request.secure_intent.id.clone(),
            cognitive_intent,
            secure_intent: request.secure_intent.clone(),
        })
    }

    pub fn validate_cancellation(&self, request_id: &str) -> BridgeResult<()> {
        if request_id.is_empty() {
            return Err(BridgeError::CancellationRequested);
        }
        Ok(())
    }

    pub fn metrics(&self) -> BridgeMetrics {
        BridgeMetrics {
            intents_processed: self.intents_processed.load(Ordering::Acquire),
            intents_rejected: self.intents_rejected.load(Ordering::Acquire),
            timeouts_enforced: self.timeouts_enforced.load(Ordering::Acquire),
        }
    }
}

impl Clone for CognitiveRuntimeBridge {
    fn clone(&self) -> Self {
        Self {
            scheduler: self.scheduler.clone(),
            registry: self.registry.clone(),
            capability_matrix: self.capability_matrix.clone(),
            intents_processed: Arc::clone(&self.intents_processed),
            intents_rejected: Arc::clone(&self.intents_rejected),
            timeouts_enforced: Arc::clone(&self.timeouts_enforced),
        }
    }
}

pub struct BridgeMetrics {
    pub intents_processed: u64,
    pub intents_rejected: u64,
    pub timeouts_enforced: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cognition::CognitiveBudget;
    use crate::integration::secure_intent::Capability;

    #[test]
    fn test_execution_request_creation() {
        let secure_intent = SecureIntent::new(
            "req-001".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        let request = ExecutionRequest::new(secure_intent);
        assert!(!request.is_expired());
    }

    #[test]
    fn test_execution_request_timeout() {
        let secure_intent = SecureIntent::new(
            "req-001".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        let mut request = ExecutionRequest::new(secure_intent);
        request.deadline_ns = 0;
        assert!(request.is_expired());
    }

    #[test]
    fn test_execution_request_time_remaining() {
        let secure_intent = SecureIntent::new(
            "req-001".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        let request = ExecutionRequest::new(secure_intent).with_timeout_ms(1000);
        let remaining = request.time_remaining_ms();
        assert!(remaining > 0 && remaining <= 1000);
    }

    #[test]
    fn test_bridge_creation() {
        let bridge = CognitiveRuntimeBridge::new(
            CognitiveScheduler::new(CognitiveBudget::standard()),
            ToolRegistry::new(),
            CapabilityMatrix::new(),
        );

        let metrics = bridge.metrics();
        assert_eq!(metrics.intents_processed, 0);
        assert_eq!(metrics.intents_rejected, 0);
    }

    #[test]
    fn test_bridge_process_valid_request() {
        let bridge = CognitiveRuntimeBridge::new(
            CognitiveScheduler::new(CognitiveBudget::standard()),
            ToolRegistry::new(),
            CapabilityMatrix::new(),
        );

        let secure_intent = SecureIntent::new(
            "test-001".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        let request = ExecutionRequest::new(secure_intent);
        let result = bridge.process_execution_request(request);

        assert!(result.is_err());
    }
}
