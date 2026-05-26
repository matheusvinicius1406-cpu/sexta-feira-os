use tokio::sync::broadcast;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum InterruptPriority {
    Low = 1,
    Medium = 2,
    Critical = 3,
    HumanVoice = 4,
}

#[derive(Debug, Clone)]
pub struct InterruptEvent {
    pub priority: InterruptPriority,
    pub source: InterruptSource,
    pub timestamp_ns: u64,
    pub context: String,
}

#[derive(Debug, Clone, Copy)]
pub enum InterruptSource {
    AudioVoiceGate,
    ScreenDelta,
    SystemTimer,
    HumanInput,
    ExternalSignal,
}

pub struct InterruptBus {
    tx: broadcast::Sender<InterruptEvent>,
    interrupt_counter: Arc<AtomicU64>,
    channel_capacity: usize,
}

impl InterruptBus {
    pub fn new(channel_capacity: usize) -> Self {
        let (tx, _) = broadcast::channel(channel_capacity);
        Self {
            tx,
            interrupt_counter: Arc::new(AtomicU64::new(0)),
            channel_capacity,
        }
    }

    pub fn trigger(&self, event: InterruptEvent) {
        self.interrupt_counter.fetch_add(1, Ordering::Relaxed);
        let _ = self.tx.send(event);
    }

    pub fn subscribe(&self) -> broadcast::Receiver<InterruptEvent> {
        self.tx.subscribe()
    }

    pub fn trigger_human_voice(&self, context: String) {
        let event = InterruptEvent {
            priority: InterruptPriority::HumanVoice,
            source: InterruptSource::HumanInput,
            timestamp_ns: timestamp_ns(),
            context,
        };
        self.trigger(event);
    }

    pub fn trigger_screen_delta(&self, context: String) {
        let event = InterruptEvent {
            priority: InterruptPriority::Medium,
            source: InterruptSource::ScreenDelta,
            timestamp_ns: timestamp_ns(),
            context,
        };
        self.trigger(event);
    }

    pub fn trigger_critical(&self, source: InterruptSource, context: String) {
        let event = InterruptEvent {
            priority: InterruptPriority::Critical,
            source,
            timestamp_ns: timestamp_ns(),
            context,
        };
        self.trigger(event);
    }

    pub fn interrupt_count(&self) -> u64 {
        self.interrupt_counter.load(Ordering::Relaxed)
    }

    pub fn receiver_count(&self) -> usize {
        self.tx.receiver_count()
    }
}

impl Clone for InterruptBus {
    fn clone(&self) -> Self {
        Self {
            tx: self.tx.clone(),
            interrupt_counter: Arc::clone(&self.interrupt_counter),
            channel_capacity: self.channel_capacity,
        }
    }
}

#[inline]
fn timestamp_ns() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_interrupt_bus_trigger() {
        let bus = InterruptBus::new(128);
        let mut rx = bus.subscribe();

        bus.trigger(InterruptEvent {
            priority: InterruptPriority::HumanVoice,
            source: InterruptSource::HumanInput,
            timestamp_ns: timestamp_ns(),
            context: "test".to_string(),
        });

        let event = tokio::time::timeout(
            std::time::Duration::from_millis(100),
            rx.recv(),
        )
        .await;

        assert!(event.is_ok());
    }

    #[test]
    fn test_priority_ordering() {
        assert!(InterruptPriority::HumanVoice > InterruptPriority::Critical);
        assert!(InterruptPriority::Critical > InterruptPriority::Medium);
        assert!(InterruptPriority::Medium > InterruptPriority::Low);
    }
}
