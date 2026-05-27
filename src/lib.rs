pub mod cognition;
pub mod integration;
pub mod perception;

pub use perception::{
    AttentionState, AudioRingBuffer, BlockHash, CognitiveContext, CognitiveSnapshot, InterruptBus,
    InterruptEvent, InterruptPriority, InterruptSource, PerceptualFunnel, PerceptualOutput,
    ScreenDeltaAnalysis, ScreenDeltaDetector, SymbolicMarker, ToolState, ToolStatus, VoiceGate,
    VoiceGateState, WindowBounds, WindowState,
};

pub use cognition::{
    CognitiveBudget, CognitiveError, CognitiveLoop, CognitiveLoopMetrics, CognitiveLoopState,
    CognitiveResult, CognitiveScheduler, DecoderMetrics, ExecutionPermit, IntentParser,
    IntentSource, ReasoningContext, SchedulerDecision, StreamDecoder, StreamState,
    StructuredIntent, ToolCapability, ToolRegistry, ToolSignature,
};

pub use integration::{
    AndroidRuntimeManager, Capability, CapabilityMatrix, CognitiveRuntimeBridge, EventMesh,
    ExecutionContext, ExecutionRequest, FlutterHudBridge, HudState, RoomEvent, RuntimeMetrics,
    RuntimeState, SecureIntent, ToolExecutor, ToolInput, ToolOutput,
};
