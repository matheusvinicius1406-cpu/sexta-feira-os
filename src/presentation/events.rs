#[derive(Debug, Clone)]
pub enum PresentationEvent {
    WakeRequested,
    SleepRequested,

    UserSpeech(String),

    AssistantResponse(String),

    ToolStarted(String),
    ToolFinished(String),

    Status(String),

    Error(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wake_requested() {
        let event = PresentationEvent::WakeRequested;
        assert!(matches!(event, PresentationEvent::WakeRequested));
    }

    #[test]
    fn test_sleep_requested() {
        let event = PresentationEvent::SleepRequested;
        assert!(matches!(event, PresentationEvent::SleepRequested));
    }

    #[test]
    fn test_user_speech_event() {
        let event = PresentationEvent::UserSpeech("hello".to_string());
        match &event {
            PresentationEvent::UserSpeech(text) => assert_eq!(text, "hello"),
            _ => panic!("Expected UserSpeech"),
        }
    }

    #[test]
    fn test_assistant_response_event() {
        let event = PresentationEvent::AssistantResponse("Hello!".to_string());
        match &event {
            PresentationEvent::AssistantResponse(response) => assert_eq!(response, "Hello!"),
            _ => panic!("Expected AssistantResponse"),
        }
    }

    #[test]
    fn test_tool_started_event() {
        let event = PresentationEvent::ToolStarted("search".to_string());
        assert!(matches!(event, PresentationEvent::ToolStarted(_)));
    }

    #[test]
    fn test_tool_finished_event() {
        let event = PresentationEvent::ToolFinished("search".to_string());
        assert!(matches!(event, PresentationEvent::ToolFinished(_)));
    }

    #[test]
    fn test_status_event() {
        let event = PresentationEvent::Status("ready".to_string());
        match &event {
            PresentationEvent::Status(msg) => assert_eq!(msg, "ready"),
            _ => panic!("Expected Status"),
        }
    }

    #[test]
    fn test_error_event() {
        let event = PresentationEvent::Error("something went wrong".to_string());
        match &event {
            PresentationEvent::Error(msg) => assert_eq!(msg, "something went wrong"),
            _ => panic!("Expected Error"),
        }
    }

    #[test]
    fn test_clone_equality() {
        let event = PresentationEvent::UserSpeech("test".to_string());
        let cloned = event.clone();
        assert!(matches!(cloned, PresentationEvent::UserSpeech(s) if s == "test"));
    }

    #[test]
    fn test_debug_format() {
        let event = PresentationEvent::Status("ok".to_string());
        let debug = format!("{:?}", event);
        assert!(debug.contains("Status"));
        assert!(debug.contains("ok"));
    }
}