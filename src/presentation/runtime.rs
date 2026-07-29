use std::sync::{Arc, RwLock};

use super::{
    PresentationEvent,
    PresentationState,
};

#[derive(Clone)]
pub struct PresentationRuntime {
    state: Arc<RwLock<PresentationState>>,
}

impl PresentationRuntime {
    pub fn new() -> Self {
        Self {
            state: Arc::new(RwLock::new(PresentationState::Idle)),
        }
    }

    pub fn state(&self) -> PresentationState {
        *self.state.read().unwrap_or_else(|e| {
            e.into_inner()  // recover from poisoned lock; process continues
        })
    }

    pub fn set_state(&self, state: PresentationState) {
        *self.state.write().unwrap_or_else(|e| {
            e.into_inner()  // recover from poisoned lock
        }) = state;
    }

    pub fn handle_event(&self, event: PresentationEvent) {
        match event {
            PresentationEvent::WakeRequested => {
                self.set_state(PresentationState::Listening);
            }

            PresentationEvent::SleepRequested => {
                self.set_state(PresentationState::Sleeping);
            }

            PresentationEvent::UserSpeech(_) => {
                self.set_state(PresentationState::Thinking);
            }

            PresentationEvent::AssistantResponse(_) => {
                self.set_state(PresentationState::Responding);
            }

            PresentationEvent::ToolStarted(_) => {
                self.set_state(PresentationState::Executing);
            }

            PresentationEvent::ToolFinished(_) => {
                self.set_state(PresentationState::Idle);
            }

            PresentationEvent::Status(_) => {}

            PresentationEvent::Error(_) => {
                self.set_state(PresentationState::Error);
            }
        }
    }
}

impl Default for PresentationRuntime {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_state_is_idle() {
        let runtime = PresentationRuntime::new();
        assert_eq!(runtime.state(), PresentationState::Idle);
    }

    #[test]
    fn test_wake_requested_sets_listening() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::WakeRequested);
        assert_eq!(runtime.state(), PresentationState::Listening);
    }

    #[test]
    fn test_sleep_requested_sets_sleeping() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::SleepRequested);
        assert_eq!(runtime.state(), PresentationState::Sleeping);
    }

    #[test]
    fn test_user_speech_sets_thinking() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::UserSpeech("hello".to_string()));
        assert_eq!(runtime.state(), PresentationState::Thinking);
    }

    #[test]
    fn test_assistant_response_sets_responding() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::AssistantResponse("Hi!".to_string()));
        assert_eq!(runtime.state(), PresentationState::Responding);
    }

    #[test]
    fn test_tool_started_sets_executing() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::ToolStarted("search".to_string()));
        assert_eq!(runtime.state(), PresentationState::Executing);
    }

    #[test]
    fn test_tool_finished_returns_to_idle() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::ToolStarted("search".to_string()));
        assert_eq!(runtime.state(), PresentationState::Executing);

        runtime.handle_event(PresentationEvent::ToolFinished("search".to_string()));
        assert_eq!(runtime.state(), PresentationState::Idle);
    }

    #[test]
    fn test_error_sets_error_state() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::Error("fail".to_string()));
        assert_eq!(runtime.state(), PresentationState::Error);
    }

    #[test]
    fn test_status_does_not_change_state() {
        let runtime = PresentationRuntime::new();
        runtime.handle_event(PresentationEvent::Status("alive".to_string()));
        assert_eq!(runtime.state(), PresentationState::Idle);
    }

    #[test]
    fn test_full_lifecycle() {
        let runtime = PresentationRuntime::new();

        runtime.handle_event(PresentationEvent::WakeRequested);
        assert_eq!(runtime.state(), PresentationState::Listening);

        runtime.handle_event(PresentationEvent::UserSpeech("what's the weather".to_string()));
        assert_eq!(runtime.state(), PresentationState::Thinking);

        runtime.handle_event(PresentationEvent::AssistantResponse("Sunny".to_string()));
        assert_eq!(runtime.state(), PresentationState::Responding);

        runtime.handle_event(PresentationEvent::ToolFinished("done".to_string()));
        assert_eq!(runtime.state(), PresentationState::Idle);
    }

    #[test]
    fn test_set_state_directly() {
        let runtime = PresentationRuntime::new();

        runtime.set_state(PresentationState::Listening);
        assert_eq!(runtime.state(), PresentationState::Listening);

        runtime.set_state(PresentationState::Thinking);
        assert_eq!(runtime.state(), PresentationState::Thinking);

        runtime.set_state(PresentationState::Sleeping);
        assert_eq!(runtime.state(), PresentationState::Sleeping);
    }

    #[test]
    fn test_clone_independence() {
        let runtime1 = PresentationRuntime::new();
        let mut runtime2 = runtime1.clone();

        runtime2.set_state(PresentationState::Listening);
        // runtime1 should be unaffected by changes to runtime2 (via Arc/RwLock)
        // Actually since they share the same Arc, they DO share state
        assert_eq!(runtime1.state(), PresentationState::Listening);
        assert_eq!(runtime2.state(), PresentationState::Listening);
    }
}