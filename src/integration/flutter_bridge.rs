use std::sync::atomic::{AtomicU64, AtomicU8, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub type HudResult<T> = Result<T, HudError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HudError {
    InvalidStateTransition,
    SyncTimeout,
    EventQueueFull,
    InvalidUpdate,
}

impl std::fmt::Display for HudError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HudError::InvalidStateTransition => write!(f, "Invalid HUD state transition"),
            HudError::SyncTimeout => write!(f, "HUD sync timeout"),
            HudError::EventQueueFull => write!(f, "HUD event queue full"),
            HudError::InvalidUpdate => write!(f, "Invalid HUD update"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HudState {
    Idle = 0,
    Listening = 1,
    Thinking = 2,
    Executing = 3,
    Error = 4,
}

impl HudState {
    pub fn from_u8(val: u8) -> Option<Self> {
        match val {
            0 => Some(HudState::Idle),
            1 => Some(HudState::Listening),
            2 => Some(HudState::Thinking),
            3 => Some(HudState::Executing),
            4 => Some(HudState::Error),
            _ => None,
        }
    }

    pub fn as_u8(&self) -> u8 {
        *self as u8
    }
}

#[derive(Debug, Clone)]
pub struct HudUpdate {
    pub state: HudState,
    pub progress: u8,
    pub message: String,
    pub timestamp_ns: u64,
}

impl HudUpdate {
    pub fn new(state: HudState) -> Self {
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            state,
            progress: 0,
            message: String::new(),
            timestamp_ns,
        }
    }

    pub fn with_progress(mut self, progress: u8) -> Self {
        self.progress = progress.min(100);
        self
    }

    pub fn with_message(mut self, msg: String) -> Self {
        self.message = msg;
        self
    }
}

pub struct FlutterHudBridge {
    current_state: Arc<AtomicU8>,
    last_update_ns: Arc<AtomicU64>,
    state_changes: Arc<AtomicU64>,
    sync_failures: Arc<AtomicU64>,
}

impl FlutterHudBridge {
    pub fn new() -> Self {
        Self {
            current_state: Arc::new(AtomicU8::new(HudState::Idle.as_u8())),
            last_update_ns: Arc::new(AtomicU64::new(0)),
            state_changes: Arc::new(AtomicU64::new(0)),
            sync_failures: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn push_update(&self, update: HudUpdate) -> HudResult<()> {
        let current = self.current_state.load(Ordering::Acquire);
        let _current_state = HudState::from_u8(current).ok_or(HudError::InvalidStateTransition)?;

        let new_state_val = update.state.as_u8();

        let valid_transitions = match HudState::from_u8(current) {
            Some(HudState::Idle) => vec![HudState::Listening, HudState::Error],
            Some(HudState::Listening) => vec![HudState::Thinking, HudState::Idle, HudState::Error],
            Some(HudState::Thinking) => vec![HudState::Executing, HudState::Idle, HudState::Error],
            Some(HudState::Executing) => vec![HudState::Idle, HudState::Error],
            Some(HudState::Error) => vec![HudState::Idle],
            None => return Err(HudError::InvalidStateTransition),
        };

        if !valid_transitions.contains(&update.state) {
            return Err(HudError::InvalidStateTransition);
        }

        self.current_state.store(new_state_val, Ordering::Release);
        self.last_update_ns
            .store(update.timestamp_ns, Ordering::Release);
        self.state_changes.fetch_add(1, Ordering::Relaxed);

        Ok(())
    }

    pub fn get_state(&self) -> HudResult<HudState> {
        let current = self.current_state.load(Ordering::Acquire);
        HudState::from_u8(current).ok_or(HudError::InvalidStateTransition)
    }

    pub fn transition_to(&self, new_state: HudState) -> HudResult<()> {
        let update = HudUpdate::new(new_state);
        self.push_update(update)
    }

    pub fn listening(&self) -> HudResult<()> {
        self.transition_to(HudState::Listening)
    }

    pub fn thinking(&self) -> HudResult<()> {
        self.transition_to(HudState::Thinking)
    }

    pub fn executing(&self) -> HudResult<()> {
        self.transition_to(HudState::Executing)
    }

    pub fn idle(&self) -> HudResult<()> {
        self.transition_to(HudState::Idle)
    }

    pub fn error(&self) -> HudResult<()> {
        self.transition_to(HudState::Error)
    }

    pub fn metrics(&self) -> HudMetrics {
        HudMetrics {
            current_state: self.get_state().ok(),
            state_changes: self.state_changes.load(Ordering::Acquire),
            sync_failures: self.sync_failures.load(Ordering::Acquire),
            last_update_ns: self.last_update_ns.load(Ordering::Acquire),
        }
    }

    pub fn last_update_age_ms(&self) -> u64 {
        let now_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        let last = self.last_update_ns.load(Ordering::Acquire);
        if now_ns >= last {
            (now_ns - last) / 1_000_000
        } else {
            0
        }
    }
}

impl Clone for FlutterHudBridge {
    fn clone(&self) -> Self {
        Self {
            current_state: Arc::clone(&self.current_state),
            last_update_ns: Arc::clone(&self.last_update_ns),
            state_changes: Arc::clone(&self.state_changes),
            sync_failures: Arc::clone(&self.sync_failures),
        }
    }
}

impl Default for FlutterHudBridge {
    fn default() -> Self {
        Self::new()
    }
}

pub struct HudMetrics {
    pub current_state: Option<HudState>,
    pub state_changes: u64,
    pub sync_failures: u64,
    pub last_update_ns: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hud_creation() {
        let hud = FlutterHudBridge::new();
        assert_eq!(hud.get_state().unwrap(), HudState::Idle);
    }

    #[test]
    fn test_hud_state_transitions() {
        let hud = FlutterHudBridge::new();

        assert!(hud.listening().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Listening);

        assert!(hud.thinking().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Thinking);

        assert!(hud.executing().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Executing);

        assert!(hud.idle().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Idle);
    }

    #[test]
    fn test_hud_invalid_transition() {
        let hud = FlutterHudBridge::new();

        assert!(hud.executing().is_err());
    }

    #[test]
    fn test_hud_error_state() {
        let hud = FlutterHudBridge::new();

        assert!(hud.listening().is_ok());
        assert!(hud.error().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Error);

        assert!(hud.idle().is_ok());
        assert_eq!(hud.get_state().unwrap(), HudState::Idle);
    }

    #[test]
    fn test_hud_metrics() {
        let hud = FlutterHudBridge::new();
        hud.listening().ok();
        hud.thinking().ok();

        let metrics = hud.metrics();
        assert_eq!(metrics.state_changes, 2);
        assert_eq!(metrics.current_state, Some(HudState::Thinking));
    }

    #[test]
    fn test_hud_update_age() {
        let hud = FlutterHudBridge::new();
        hud.listening().ok();

        let age = hud.last_update_age_ms();
        assert!(age < 100);
    }
}
