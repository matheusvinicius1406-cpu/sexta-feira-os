#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PresentationState {
    Sleeping,
    Idle,
    Listening,
    Thinking,
    Responding,
    Executing,
    Error,
}

impl PresentationState {
    pub fn is_awake(&self) -> bool {
        !matches!(self, PresentationState::Sleeping)
    }

    pub fn is_busy(&self) -> bool {
        matches!(
            self,
            PresentationState::Thinking
                | PresentationState::Responding
                | PresentationState::Executing
        )
    }
}