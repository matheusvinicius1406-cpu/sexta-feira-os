use std::collections::HashMap;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub struct CognitiveSnapshot {
    pub timestamp_ns: u64,
    pub context: CognitiveContext,
    pub focus_hash: u64,
    pub active_window: Option<WindowState>,
    pub tool_states: Arc<ToolStateMap>,
    pub symbolic_markers: Arc<SymbolicMarkers>,
}

#[derive(Debug, Clone)]
pub struct CognitiveContext {
    pub user_intent: Option<String>,
    pub conversation_id: String,
    pub memory_horizon_ms: u64,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct WindowState {
    pub window_id: u64,
    pub title: String,
    pub bounds: WindowBounds,
    pub is_focused: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct WindowBounds {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

pub type ToolStateMap = HashMap<String, ToolState>;

#[derive(Debug, Clone)]
pub struct ToolState {
    pub name: String,
    pub status: ToolStatus,
    pub input_hash: u64,
    pub output_hash: u64,
    pub duration_ns: u64,
    pub invocation_count: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToolStatus {
    Ready,
    Executing,
    Completed,
    Failed,
    Blocked,
}

pub type SymbolicMarkers = HashMap<String, SymbolicMarker>;

#[derive(Debug, Clone)]
pub struct SymbolicMarker {
    pub key: String,
    pub value: String,
    pub confidence: f32,
    pub created_at_ns: u64,
    pub expires_at_ns: Option<u64>,
}

impl CognitiveSnapshot {
    pub fn new(conversation_id: String) -> Self {
        Self {
            timestamp_ns: current_time_ns(),
            context: CognitiveContext {
                user_intent: None,
                conversation_id,
                memory_horizon_ms: 3600000,
                metadata: HashMap::new(),
            },
            focus_hash: 0,
            active_window: None,
            tool_states: Arc::new(HashMap::new()),
            symbolic_markers: Arc::new(HashMap::new()),
        }
    }

    pub fn with_intent(mut self, intent: String) -> Self {
        self.context.user_intent = Some(intent);
        self
    }

    pub fn with_window(mut self, window: WindowState) -> Self {
        self.active_window = Some(window);
        self
    }

    pub fn with_memory_horizon(mut self, ms: u64) -> Self {
        self.context.memory_horizon_ms = ms;
        self
    }

    pub fn add_metadata(&mut self, key: String, value: String) {
        self.context.metadata.insert(key, value);
    }

    pub fn set_focus_hash(&mut self, hash: u64) {
        self.focus_hash = hash;
    }

    pub fn add_tool_state(&mut self, tool: ToolState) {
        // Use make_mut to handle shared Arcs: clones the inner data on write.
        Arc::make_mut(&mut self.tool_states).insert(tool.name.clone(), tool);
    }

    pub fn get_tool_state(&self, tool_name: &str) -> Option<ToolState> {
        self.tool_states.get(tool_name).cloned()
    }

    pub fn add_symbolic_marker(&mut self, marker: SymbolicMarker) {
        Arc::make_mut(&mut self.symbolic_markers).insert(marker.key.clone(), marker);
    }

    pub fn get_symbolic_marker(&self, key: &str) -> Option<SymbolicMarker> {
        self.symbolic_markers.get(key).cloned()
    }

    pub fn is_marker_expired(&self, marker: &SymbolicMarker) -> bool {
        if let Some(expires_at) = marker.expires_at_ns {
            self.timestamp_ns >= expires_at
        } else {
            false
        }
    }

    pub fn cleanup_expired_markers(&mut self) {
        let now = current_time_ns();
        Arc::make_mut(&mut self.symbolic_markers).retain(|_, marker| {
            if let Some(expires_at) = marker.expires_at_ns {
                now < expires_at
            } else {
                true
            }
        });
    }

    pub fn merge(&mut self, other: CognitiveSnapshot) {
        if let Some(intent) = other.context.user_intent {
            self.context.user_intent = Some(intent);
        }

        self.context.memory_horizon_ms = other.context.memory_horizon_ms;

        for (key, value) in other.context.metadata {
            self.context.metadata.insert(key, value);
        }

        if let Some(window) = other.active_window {
            self.active_window = Some(window);
        }

        for (name, tool_state) in other.tool_states.iter() {
            Arc::make_mut(&mut self.tool_states).insert(name.clone(), tool_state.clone());
        }

        for (key, marker) in other.symbolic_markers.iter() {
            Arc::make_mut(&mut self.symbolic_markers).insert(key.clone(), marker.clone());
        }

        self.timestamp_ns = current_time_ns();
    }

    pub fn compute_snapshot_hash(&self) -> u64 {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        hash ^= self.focus_hash;
        hash = hash.wrapping_mul(PRIME);

        hash ^= self.tool_states.len() as u64;
        hash = hash.wrapping_mul(PRIME);

        hash ^= self.symbolic_markers.len() as u64;
        hash = hash.wrapping_mul(PRIME);

        if let Some(window) = &self.active_window {
            hash ^= window.window_id;
            hash = hash.wrapping_mul(PRIME);
        }

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

impl WindowBounds {
    pub fn area(&self) -> u64 {
        (self.width as u64) * (self.height as u64)
    }

    pub fn contains_point(&self, px: i32, py: i32) -> bool {
        px >= self.x
            && px < (self.x + self.width as i32)
            && py >= self.y
            && py < (self.y + self.height as i32)
    }
}

impl SymbolicMarker {
    pub fn new(key: String, value: String, confidence: f32) -> Self {
        Self {
            key,
            value,
            confidence: confidence.clamp(0.0, 1.0),
            created_at_ns: current_time_ns(),
            expires_at_ns: None,
        }
    }

    pub fn with_ttl(mut self, ttl_ms: u64) -> Self {
        let now_ns = current_time_ns();
        self.expires_at_ns = Some(now_ns + ttl_ms * 1_000_000);
        self
    }
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
    fn test_cognitive_snapshot_creation() {
        let snapshot = CognitiveSnapshot::new("conv-001".to_string());
        assert_eq!(snapshot.context.conversation_id, "conv-001");
        assert!(snapshot.context.user_intent.is_none());
    }

    #[test]
    fn test_cognitive_snapshot_with_intent() {
        let snapshot =
            CognitiveSnapshot::new("conv-001".to_string()).with_intent("find_files".to_string());
        assert_eq!(snapshot.context.user_intent, Some("find_files".to_string()));
    }

    #[test]
    fn test_window_bounds_contains_point() {
        let bounds = WindowBounds {
            x: 100,
            y: 200,
            width: 500,
            height: 300,
        };

        assert!(bounds.contains_point(150, 250));
        assert!(!bounds.contains_point(50, 250));
        assert!(!bounds.contains_point(700, 250));
    }

    #[test]
    fn test_symbolic_marker_with_ttl() {
        let marker =
            SymbolicMarker::new("focus".to_string(), "window_1".to_string(), 0.95).with_ttl(5000);

        assert!(marker.expires_at_ns.is_some());
    }

    #[test]
    fn test_tool_state_management() {
        let mut snapshot = CognitiveSnapshot::new("conv-001".to_string());

        let tool = ToolState {
            name: "search".to_string(),
            status: ToolStatus::Executing,
            input_hash: 123,
            output_hash: 456,
            duration_ns: 1_000_000,
            invocation_count: 1,
        };

        snapshot.add_tool_state(tool.clone());
        let retrieved = snapshot.get_tool_state("search");

        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().status, ToolStatus::Executing);
    }

    #[test]
    fn test_cleanup_expired_markers() {
        let mut snapshot = CognitiveSnapshot::new("conv-001".to_string());

        let marker_expired =
            SymbolicMarker::new("old".to_string(), "value".to_string(), 0.5).with_ttl(1);

        snapshot.add_symbolic_marker(marker_expired);

        std::thread::sleep(std::time::Duration::from_millis(10));
        snapshot.cleanup_expired_markers();

        assert!(snapshot.get_symbolic_marker("old").is_none());
    }
}
