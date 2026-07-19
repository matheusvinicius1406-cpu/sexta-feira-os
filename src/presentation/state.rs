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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sleeping_is_not_awake() {
        assert!(!PresentationState::Sleeping.is_awake());
    }

    #[test]
    fn test_idle_is_awake() {
        assert!(PresentationState::Idle.is_awake());
    }

    #[test]
    fn test_listening_is_awake() {
        assert!(PresentationState::Listening.is_awake());
    }

    #[test]
    fn test_thinking_is_busy() {
        assert!(PresentationState::Thinking.is_busy());
    }

    #[test]
    fn test_responding_is_busy() {
        assert!(PresentationState::Responding.is_busy());
    }

    #[test]
    fn test_executing_is_busy() {
        assert!(PresentationState::Executing.is_busy());
    }

    #[test]
    fn test_sleeping_is_not_busy() {
        assert!(!PresentationState::Sleeping.is_busy());
    }

    #[test]
    fn test_idle_is_not_busy() {
        assert!(!PresentationState::Idle.is_busy());
    }

    #[test]
    fn test_listening_is_not_busy() {
        assert!(!PresentationState::Listening.is_busy());
    }

    #[test]
    fn test_error_is_not_busy() {
        assert!(!PresentationState::Error.is_busy());
    }

    #[test]
    fn test_all_states_have_correct_awake() {
        let states = [
            (PresentationState::Sleeping, false),
            (PresentationState::Idle, true),
            (PresentationState::Listening, true),
            (PresentationState::Thinking, true),
            (PresentationState::Responding, true),
            (PresentationState::Executing, true),
            (PresentationState::Error, true),
        ];
        for (state, expected_awake) in states {
            assert_eq!(state.is_awake(), expected_awake, "{:?}.is_awake()", state);
        }
    }

    #[test]
    fn test_clone_and_eq() {
        let a = PresentationState::Thinking;
        let b = a.clone();
        assert_eq!(a, b);
        assert_ne!(a, PresentationState::Idle);
    }

    #[test]
    fn test_debug_output() {
        let debug = format!("{:?}", PresentationState::Executing);
        assert_eq!(debug, "Executing");
    }
}