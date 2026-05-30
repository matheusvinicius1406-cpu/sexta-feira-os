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
        *self.state.read().unwrap()
    }

    pub fn set_state(&self, state: PresentationState) {
        *self.state.write().unwrap() = state;
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