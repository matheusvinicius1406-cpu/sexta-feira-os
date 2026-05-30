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