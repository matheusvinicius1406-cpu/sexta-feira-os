use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::sync::broadcast;

pub type EventResult<T> = Result<T, EventError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EventError {
    ChannelClosed,
    SendFailed,
    QueueFull,
    BackpressureTriggered,
}

impl std::fmt::Display for EventError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EventError::ChannelClosed => write!(f, "Channel closed"),
            EventError::SendFailed => write!(f, "Send failed"),
            EventError::QueueFull => write!(f, "Event queue full"),
            EventError::BackpressureTriggered => write!(f, "Backpressure triggered"),
        }
    }
}

#[derive(Debug, Clone)]
pub enum RoomEvent {
    CognitiveIntent(String),
    PerceptionTrigger(String),
    ToolExecutionStart(String),
    ToolExecutionComplete(String),
    ToolExecutionFailed(String),
    HumanInterrupt(String),
    SystemEvent(String),
    StateChange(String),
}

pub struct EventMesh {
    tx: broadcast::Sender<RoomEvent>,
    events_sent: Arc<AtomicU64>,
    events_dropped: Arc<AtomicU64>,
    backpressure_high: Arc<AtomicU64>,
    capacity: usize,
}

impl EventMesh {
    pub fn new(capacity: usize) -> Self {
        let (tx, _rx) = broadcast::channel(capacity);
        Self {
            tx,
            events_sent: Arc::new(AtomicU64::new(0)),
            events_dropped: Arc::new(AtomicU64::new(0)),
            backpressure_high: Arc::new(AtomicU64::new(0)),
            capacity,
        }
    }

    pub fn publish(&self, event: RoomEvent) -> EventResult<()> {
        let subscriber_count = self.tx.receiver_count();

        if subscriber_count == 0 {
            self.events_dropped.fetch_add(1, Ordering::Relaxed);
            return Ok(());
        }

        match self.tx.send(event) {
            Ok(remaining) => {
                // `send` returns the number of remaining slots when successful.
                // Low remaining capacity ≈ backpressure building up.
                self.events_sent.fetch_add(1, Ordering::Relaxed);
                if remaining < self.capacity / 4 {
                    self.backpressure_high.fetch_add(1, Ordering::Relaxed);
                }
                Ok(())
            }
            Err(_e) => {
                // broadcast::SendError — all receivers lagged behind.
                self.events_dropped.fetch_add(1, Ordering::Relaxed);
                self.backpressure_high.fetch_add(1, Ordering::Relaxed);
                Err(EventError::BackpressureTriggered)
            }
        }
    }

    pub fn subscribe(&self) -> EventResult<broadcast::Receiver<RoomEvent>> {
        Ok(self.tx.subscribe())
    }

    pub fn metrics(&self) -> EventMeshMetrics {
        EventMeshMetrics {
            events_sent: self.events_sent.load(Ordering::Acquire),
            events_dropped: self.events_dropped.load(Ordering::Acquire),
            backpressure_high: self.backpressure_high.load(Ordering::Acquire),
            capacity: self.capacity,
            active_subscribers: self.tx.receiver_count(),
        }
    }
}

impl Clone for EventMesh {
    fn clone(&self) -> Self {
        Self {
            tx: self.tx.clone(),
            events_sent: Arc::clone(&self.events_sent),
            events_dropped: Arc::clone(&self.events_dropped),
            backpressure_high: Arc::clone(&self.backpressure_high),
            capacity: self.capacity,
        }
    }
}

pub struct EventMeshMetrics {
    pub events_sent: u64,
    pub events_dropped: u64,
    pub backpressure_high: u64,
    pub capacity: usize,
    pub active_subscribers: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_event_mesh_creation() {
        let mesh = EventMesh::new(100);
        let metrics = mesh.metrics();

        assert_eq!(metrics.events_sent, 0);
        assert_eq!(metrics.events_dropped, 0);
        assert_eq!(metrics.capacity, 100);
    }

    #[test]
    fn test_event_mesh_publish_no_subscribers() {
        let mesh = EventMesh::new(100);
        let event = RoomEvent::SystemEvent("test".to_string());

        let result = mesh.publish(event);
        assert!(result.is_ok() || result == Err(EventError::SendFailed));
    }

    #[tokio::test]
    async fn test_event_mesh_publish_with_subscriber() {
        let mesh = EventMesh::new(100);
        let mut rx = mesh.subscribe().unwrap();

        let event = RoomEvent::SystemEvent("test-event".to_string());
        assert!(mesh.publish(event.clone()).is_ok());

        let received = tokio::time::timeout(std::time::Duration::from_millis(100), rx.recv()).await;

        assert!(received.is_ok());
    }

    #[test]
    fn test_event_mesh_metrics() {
        let mesh = EventMesh::new(50);
        let _rx = mesh.subscribe().ok();

        let event = RoomEvent::CognitiveIntent("intent-1".to_string());
        let _ = mesh.publish(event);

        let metrics = mesh.metrics();
        assert!(metrics.active_subscribers > 0);
    }
}
