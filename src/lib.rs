pub mod perception;
pub mod cognition;

pub use perception::{
    InterruptBus, InterruptEvent, InterruptPriority, InterruptSource,
    AudioRingBuffer,
    VoiceGate, VoiceGateState,
    ScreenDeltaDetector, ScreenDeltaAnalysis, BlockHash,
    PerceptualFunnel, PerceptualOutput, AttentionState,
    CognitiveSnapshot, CognitiveContext, WindowState, WindowBounds,
    ToolState, ToolStatus, SymbolicMarker,
};

pub use cognition::{
    CognitiveError, CognitiveResult,
    StructuredIntent, IntentSource,
    IntentParser,
    StreamDecoder, StreamState, DecoderMetrics,
    CognitiveScheduler, CognitiveBudget, SchedulerDecision, ExecutionPermit,
    ReasoningContext,
    ToolRegistry, ToolSignature, ToolCapability,
    CognitiveLoop, CognitiveLoopState, CognitiveLoopMetrics,
};
