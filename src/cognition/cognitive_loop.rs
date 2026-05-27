use crate::cognition::cognitive_errors::{CognitiveError, CognitiveResult};
use crate::cognition::cognitive_scheduler::CognitiveScheduler;
use crate::cognition::intent_parser::IntentParser;
use crate::cognition::reasoning_context::ReasoningContext;
use crate::cognition::stream_decoder::StreamDecoder;
use crate::cognition::structured_intent::StructuredIntent;
use crate::cognition::tool_registry::ToolRegistry;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CognitiveLoopState {
    Idle,
    Processing,
    Waiting,
    Shutdown,
}

pub struct CognitiveLoopMetrics {
    pub intents_processed: Arc<AtomicU64>,
    pub errors: Arc<AtomicU64>,
    pub stream_resets: Arc<AtomicU64>,
}

impl CognitiveLoopMetrics {
    pub fn new() -> Self {
        Self {
            intents_processed: Arc::new(AtomicU64::new(0)),
            errors: Arc::new(AtomicU64::new(0)),
            stream_resets: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn record_intent(&self) {
        self.intents_processed.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_error(&self) {
        self.errors.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_stream_reset(&self) {
        self.stream_resets.fetch_add(1, Ordering::Relaxed);
    }

    pub fn get_intents_processed(&self) -> u64 {
        self.intents_processed.load(Ordering::Acquire)
    }

    pub fn get_errors(&self) -> u64 {
        self.errors.load(Ordering::Acquire)
    }

    pub fn get_stream_resets(&self) -> u64 {
        self.stream_resets.load(Ordering::Acquire)
    }
}

pub struct CognitiveLoop {
    state: CognitiveLoopState,
    scheduler: CognitiveScheduler,
    context: ReasoningContext,
    registry: ToolRegistry,
    decoder: StreamDecoder,
    metrics: CognitiveLoopMetrics,
}

impl CognitiveLoop {
    pub fn new(scheduler: CognitiveScheduler, registry: ToolRegistry) -> Self {
        Self {
            state: CognitiveLoopState::Idle,
            scheduler,
            context: ReasoningContext::new(),
            registry,
            decoder: StreamDecoder::new(1_000_000),
            metrics: CognitiveLoopMetrics::new(),
        }
    }

    pub fn process_stream_chunk(&mut self, chunk: &str) -> CognitiveResult<()> {
        if self.state == CognitiveLoopState::Shutdown {
            return Err(CognitiveError::CognitivePanic(
                "Loop is shutdown".to_string(),
            ));
        }

        self.state = CognitiveLoopState::Processing;

        match self.decoder.process_chunk(chunk) {
            Ok(Some(complete_payload)) => {
                self.process_complete_intent(&complete_payload)?;
                self.metrics.record_intent();
            }
            Ok(None) => {
                self.state = CognitiveLoopState::Waiting;
            }
            Err(e) => {
                self.metrics.record_error();
                self.decoder.reset();
                self.metrics.record_stream_reset();
                return Err(e);
            }
        }

        Ok(())
    }

    pub fn flush_pending(&mut self) -> CognitiveResult<()> {
        if self.state == CognitiveLoopState::Shutdown {
            return Err(CognitiveError::CognitivePanic(
                "Loop is shutdown".to_string(),
            ));
        }

        match self.decoder.try_flush() {
            Ok(Some(payload)) => {
                self.process_complete_intent(&payload)?;
                self.metrics.record_intent();
            }
            Ok(None) => {
                self.state = CognitiveLoopState::Idle;
            }
            Err(e) => {
                self.metrics.record_error();
                self.decoder.reset();
                self.metrics.record_stream_reset();
                return Err(e);
            }
        }

        Ok(())
    }

    pub fn dispatch_intent(&mut self, intent: StructuredIntent) -> CognitiveResult<()> {
        if !intent.is_valid() {
            return Err(CognitiveError::InvalidIntent(
                "Intent validation failed".to_string(),
            ));
        }

        let permit = self.scheduler.request_execution()?;

        self.scheduler.enforce_execution_limits(&permit)?;

        if !self.registry.tool_exists(&intent.requested_tool) {
            return Err(CognitiveError::ToolNotFound(intent.requested_tool.clone()));
        }

        self.context.add_to_history(intent.clone());
        self.context
            .update_focus(intent.requested_tool.clone(), intent);

        Ok(())
    }

    pub fn handle_interrupt(&mut self) {
        self.scheduler.request_preemption();
        self.state = CognitiveLoopState::Idle;
    }

    pub fn shutdown(&mut self) {
        self.state = CognitiveLoopState::Shutdown;
        self.decoder.reset();
        self.context.clear_focus();
    }

    pub fn current_state(&self) -> CognitiveLoopState {
        self.state
    }

    pub fn context(&self) -> &ReasoningContext {
        &self.context
    }

    pub fn metrics(&self) -> &CognitiveLoopMetrics {
        &self.metrics
    }

    fn process_complete_intent(&mut self, payload: &str) -> CognitiveResult<()> {
        let intent = IntentParser::parse_complete_intent(payload)?;
        self.dispatch_intent(intent)?;
        Ok(())
    }
}

impl Default for CognitiveLoop {
    fn default() -> Self {
        Self::new(CognitiveScheduler::default(), ToolRegistry::new())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cognition::cognitive_scheduler::CognitiveBudget;
    use crate::cognition::tool_registry::ToolSignature;

    #[test]
    fn test_cognitive_loop_creation() {
        let loop_instance = CognitiveLoop::new(
            CognitiveScheduler::new(CognitiveBudget::default()),
            ToolRegistry::new(),
        );

        assert_eq!(loop_instance.current_state(), CognitiveLoopState::Idle);
    }

    #[test]
    fn test_dispatch_intent() {
        let scheduler = CognitiveScheduler::new(CognitiveBudget::default());
        let mut registry = ToolRegistry::new();

        let sig = ToolSignature::new("search".to_string(), "1.0".to_string());
        registry.register_tool(sig).unwrap();

        let mut loop_instance = CognitiveLoop::new(scheduler, registry);

        let intent = StructuredIntent::new(
            "test-001".to_string(),
            "search".to_string(),
            crate::cognition::structured_intent::IntentSource::HumanVoice,
        );

        let result = loop_instance.dispatch_intent(intent);
        assert!(result.is_ok());
    }

    #[test]
    fn test_metrics_recording() {
        let loop_instance = CognitiveLoop::new(
            CognitiveScheduler::new(CognitiveBudget::default()),
            ToolRegistry::new(),
        );

        assert_eq!(loop_instance.metrics().get_intents_processed(), 0);
    }
}
