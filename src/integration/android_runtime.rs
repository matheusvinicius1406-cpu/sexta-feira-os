use std::sync::atomic::{AtomicU64, AtomicU8, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub type RuntimeResult<T> = Result<T, RuntimeError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeError {
    InvalidStateTransition(u8),
    ServiceNotRunning,
    InitializationFailed(u8),
    LifecycleViolation,
    RecoveryFailed,
}

impl std::fmt::Display for RuntimeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RuntimeError::InvalidStateTransition(state) => {
                write!(f, "Invalid state transition from {}", state)
            }
            RuntimeError::ServiceNotRunning => write!(f, "Service is not running"),
            RuntimeError::InitializationFailed(code) => {
                write!(f, "Initialization failed: {}", code)
            }
            RuntimeError::LifecycleViolation => write!(f, "Lifecycle violation"),
            RuntimeError::RecoveryFailed => write!(f, "Recovery failed"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuntimeState {
    Uninitialized = 0,
    Initializing = 1,
    Running = 2,
    Paused = 3,
    Stopping = 4,
    Stopped = 5,
    Error = 6,
}

impl RuntimeState {
    pub fn from_u8(val: u8) -> Option<Self> {
        match val {
            0 => Some(RuntimeState::Uninitialized),
            1 => Some(RuntimeState::Initializing),
            2 => Some(RuntimeState::Running),
            3 => Some(RuntimeState::Paused),
            4 => Some(RuntimeState::Stopping),
            5 => Some(RuntimeState::Stopped),
            6 => Some(RuntimeState::Error),
            _ => None,
        }
    }

    pub fn as_u8(&self) -> u8 {
        *self as u8
    }
}

pub struct AndroidRuntimeMetrics {
    pub state_transitions: u64,
    pub foreground_activations: u64,
    pub background_deactivations: u64,
    pub wake_cycles: u64,
    pub recovery_attempts: u64,
}

pub struct AndroidRuntimeManager {
    state: Arc<AtomicU8>,
    is_foreground: Arc<AtomicU8>,
    battery_saver_active: Arc<AtomicU8>,
    thermal_throttle: Arc<AtomicU8>,
    state_transitions: Arc<AtomicU64>,
    foreground_activations: Arc<AtomicU64>,
    wake_cycles: Arc<AtomicU64>,
    last_state_change_ns: Arc<AtomicU64>,
}

impl AndroidRuntimeManager {
    pub fn new() -> Self {
        Self {
            state: Arc::new(AtomicU8::new(RuntimeState::Uninitialized.as_u8())),
            is_foreground: Arc::new(AtomicU8::new(0)),
            battery_saver_active: Arc::new(AtomicU8::new(0)),
            thermal_throttle: Arc::new(AtomicU8::new(0)),
            state_transitions: Arc::new(AtomicU64::new(0)),
            foreground_activations: Arc::new(AtomicU64::new(0)),
            wake_cycles: Arc::new(AtomicU64::new(0)),
            last_state_change_ns: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn initialize(&self) -> RuntimeResult<()> {
        let current = self.state.load(Ordering::Acquire);
        let current_state =
            RuntimeState::from_u8(current).ok_or(RuntimeError::InitializationFailed(1))?;

        if current_state != RuntimeState::Uninitialized {
            return Err(RuntimeError::InvalidStateTransition(current));
        }

        self.state
            .store(RuntimeState::Initializing.as_u8(), Ordering::Release);
        self.record_state_transition();
        self.state
            .store(RuntimeState::Running.as_u8(), Ordering::Release);
        self.record_state_transition();

        Ok(())
    }

    pub fn on_foreground(&self) -> RuntimeResult<()> {
        let current = self.state.load(Ordering::Acquire);
        let current_state =
            RuntimeState::from_u8(current).ok_or(RuntimeError::ServiceNotRunning)?;

        if current_state == RuntimeState::Stopped || current_state == RuntimeState::Error {
            return Err(RuntimeError::LifecycleViolation);
        }

        self.is_foreground.store(1, Ordering::Release);
        self.foreground_activations.fetch_add(1, Ordering::Relaxed);
        self.state
            .store(RuntimeState::Running.as_u8(), Ordering::Release);
        self.record_state_transition();

        Ok(())
    }

    pub fn on_background(&self) -> RuntimeResult<()> {
        let current = self.state.load(Ordering::Acquire);
        let current_state =
            RuntimeState::from_u8(current).ok_or(RuntimeError::ServiceNotRunning)?;

        if current_state != RuntimeState::Running {
            return Err(RuntimeError::InvalidStateTransition(current));
        }

        self.is_foreground.store(0, Ordering::Release);
        self.state
            .store(RuntimeState::Paused.as_u8(), Ordering::Release);
        self.record_state_transition();

        Ok(())
    }

    pub fn set_battery_saver(&self, enabled: bool) {
        let val = if enabled { 1 } else { 0 };
        self.battery_saver_active.store(val, Ordering::Release);
    }

    pub fn set_thermal_throttle(&self, level: u8) {
        self.thermal_throttle.store(level.min(3), Ordering::Release);
    }

    pub fn request_wake_lock(&self) -> RuntimeResult<()> {
        let current = self.state.load(Ordering::Acquire);
        let current_state =
            RuntimeState::from_u8(current).ok_or(RuntimeError::ServiceNotRunning)?;

        if current_state == RuntimeState::Stopped {
            return Err(RuntimeError::LifecycleViolation);
        }

        self.wake_cycles.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }

    pub fn should_use_degraded_mode(&self) -> bool {
        let battery = self.battery_saver_active.load(Ordering::Acquire);
        let thermal = self.thermal_throttle.load(Ordering::Acquire);

        battery != 0 || thermal >= 2
    }

    pub fn get_state(&self) -> RuntimeResult<RuntimeState> {
        let current = self.state.load(Ordering::Acquire);
        RuntimeState::from_u8(current).ok_or(RuntimeError::InvalidStateTransition(current))
    }

    pub fn shutdown(&self) -> RuntimeResult<()> {
        let current = self.state.load(Ordering::Acquire);
        let _ = RuntimeState::from_u8(current).ok_or(RuntimeError::ServiceNotRunning)?;

        self.state
            .store(RuntimeState::Stopping.as_u8(), Ordering::Release);
        self.record_state_transition();
        self.state
            .store(RuntimeState::Stopped.as_u8(), Ordering::Release);
        self.record_state_transition();

        Ok(())
    }

    pub fn metrics(&self) -> AndroidRuntimeMetrics {
        AndroidRuntimeMetrics {
            state_transitions: self.state_transitions.load(Ordering::Acquire),
            foreground_activations: self.foreground_activations.load(Ordering::Acquire),
            background_deactivations: 0,
            wake_cycles: self.wake_cycles.load(Ordering::Acquire),
            recovery_attempts: 0,
        }
    }

    fn record_state_transition(&self) {
        self.state_transitions.fetch_add(1, Ordering::Relaxed);
        let now_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;
        self.last_state_change_ns.store(now_ns, Ordering::Release);
    }
}

impl Clone for AndroidRuntimeManager {
    fn clone(&self) -> Self {
        Self {
            state: Arc::clone(&self.state),
            is_foreground: Arc::clone(&self.is_foreground),
            battery_saver_active: Arc::clone(&self.battery_saver_active),
            thermal_throttle: Arc::clone(&self.thermal_throttle),
            state_transitions: Arc::clone(&self.state_transitions),
            foreground_activations: Arc::clone(&self.foreground_activations),
            wake_cycles: Arc::clone(&self.wake_cycles),
            last_state_change_ns: Arc::clone(&self.last_state_change_ns),
        }
    }
}

impl Default for AndroidRuntimeManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_runtime_creation() {
        let runtime = AndroidRuntimeManager::new();
        assert_eq!(runtime.get_state().unwrap(), RuntimeState::Uninitialized);
    }

    #[test]
    fn test_runtime_initialization() {
        let runtime = AndroidRuntimeManager::new();
        assert!(runtime.initialize().is_ok());
        assert_eq!(runtime.get_state().unwrap(), RuntimeState::Running);
    }

    #[test]
    fn test_foreground_background_transitions() {
        let runtime = AndroidRuntimeManager::new();
        runtime.initialize().unwrap();

        assert!(runtime.on_foreground().is_ok());
        assert_eq!(runtime.get_state().unwrap(), RuntimeState::Running);

        assert!(runtime.on_background().is_ok());
        assert_eq!(runtime.get_state().unwrap(), RuntimeState::Paused);
    }

    #[test]
    fn test_battery_saver_degraded_mode() {
        let runtime = AndroidRuntimeManager::new();
        runtime.initialize().unwrap();

        runtime.set_battery_saver(true);
        assert!(runtime.should_use_degraded_mode());

        runtime.set_battery_saver(false);
        assert!(!runtime.should_use_degraded_mode());
    }

    #[test]
    fn test_thermal_throttle() {
        let runtime = AndroidRuntimeManager::new();
        runtime.initialize().unwrap();

        runtime.set_thermal_throttle(3);
        assert!(runtime.should_use_degraded_mode());
    }

    #[test]
    fn test_wake_lock() {
        let runtime = AndroidRuntimeManager::new();
        runtime.initialize().unwrap();

        assert!(runtime.request_wake_lock().is_ok());

        let metrics = runtime.metrics();
        assert_eq!(metrics.wake_cycles, 1);
    }
}
