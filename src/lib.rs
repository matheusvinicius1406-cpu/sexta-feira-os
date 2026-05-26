pub mod perception;

pub use perception::{
    InterruptBus, InterruptEvent, InterruptPriority, InterruptSource,
    AudioRingBuffer,
    VoiceGate, VoiceGateState,
    ScreenDeltaDetector, ScreenDeltaAnalysis, BlockHash,
    PerceptualFunnel, PerceptualOutput, AttentionState,
    CognitiveSnapshot, CognitiveContext, WindowState, WindowBounds,
    ToolState, ToolStatus, SymbolicMarker,
};
