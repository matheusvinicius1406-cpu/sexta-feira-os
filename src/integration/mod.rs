pub mod android_runtime;
pub mod cognitive_bridge;
pub mod event_mesh;
pub mod flutter_bridge;
pub mod observability;
pub mod secure_intent;
pub mod tool_executor;

pub use android_runtime::{
    AndroidRuntimeManager, AndroidRuntimeMetrics, RuntimeError, RuntimeResult, RuntimeState,
};
pub use cognitive_bridge::{
    BridgeError, BridgeMetrics, BridgeResult, CognitiveRuntimeBridge, ExecutionContext,
    ExecutionRequest,
};
pub use event_mesh::{EventError, EventMesh, EventMeshMetrics, RoomEvent};
pub use flutter_bridge::{FlutterHudBridge, HudError, HudMetrics, HudResult, HudState, HudUpdate};
pub use observability::{RuntimeMetrics, RuntimeMetricsSnapshot};
pub use secure_intent::{
    Capability, CapabilityMatrix, SecureIntent, SecurityError, SecurityResult,
};
pub use tool_executor::{
    ToolError, ToolExecutor, ToolInput, ToolOutput, ToolOutputStatus, ToolResult,
};
