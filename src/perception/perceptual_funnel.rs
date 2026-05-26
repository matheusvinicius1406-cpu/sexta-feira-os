use crate::perception::interrupt_bus::{InterruptBus, InterruptEvent};
use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub enum PerceptualOutput {
    Idle,
    DropEvent,
    WakeCognitiveCore { context_trigger: String },
}

pub struct PerceptualFunnel {
    interrupt_bus: InterruptBus,
    attention_state: Arc<AtomicU8>,
    voice_weight: f32,
    visual_weight: f32,
    last_wake_time: Arc<std::sync::Mutex<u64>>,
    wake_debounce_ms: u64,
}

impl PerceptualFunnel {
    pub fn new(interrupt_bus: InterruptBus) -> Self {
        Self {
            interrupt_bus,
            attention_state: Arc::new(AtomicU8::new(AttentionState::Idle as u8)),
            voice_weight: 0.8,
            visual_weight: 0.2,
            last_wake_time: Arc::new(std::sync::Mutex::new(0)),
            wake_debounce_ms: 500,
        }
    }

    pub fn evaluate_attention(&self, event: &InterruptEvent) -> PerceptualOutput {
        use crate::perception::interrupt_bus::InterruptPriority;
        use crate::perception::interrupt_bus::InterruptSource;

        match event.priority {
            InterruptPriority::HumanVoice => {
                self.set_attention_state(AttentionState::HighAlert);
                PerceptualOutput::WakeCognitiveCore {
                    context_trigger: format!(
                        "human_voice:{}",
                        event.context
                    ),
                }
            }
            InterruptPriority::Critical => {
                self.set_attention_state(AttentionState::HighAlert);
                PerceptualOutput::WakeCognitiveCore {
                    context_trigger: format!(
                        "critical:{}",
                        event.context
                    ),
                }
            }
            InterruptPriority::Medium => {
                if matches!(event.source, InterruptSource::ScreenDelta) {
                    if self.should_debounce_wake() {
                        PerceptualOutput::Idle
                    } else {
                        self.set_attention_state(AttentionState::Attentive);
                        PerceptualOutput::WakeCognitiveCore {
                            context_trigger: format!(
                                "visual_delta:{}",
                                event.context
                            ),
                        }
                    }
                } else {
                    PerceptualOutput::DropEvent
                }
            }
            InterruptPriority::Low => PerceptualOutput::DropEvent,
        }
    }

    pub fn process_interrupt_batch(&self, events: Vec<InterruptEvent>) -> Vec<PerceptualOutput> {
        events
            .into_iter()
            .map(|event| self.evaluate_attention(&event))
            .collect()
    }

    pub fn current_attention_state(&self) -> AttentionState {
        let state_byte = self.attention_state.load(Ordering::Acquire);
        match state_byte {
            0 => AttentionState::Idle,
            1 => AttentionState::Attentive,
            2 => AttentionState::HighAlert,
            _ => AttentionState::Idle,
        }
    }

    pub fn set_voice_weight(&mut self, weight: f32) {
        self.voice_weight = weight.clamp(0.0, 1.0);
    }

    pub fn set_visual_weight(&mut self, weight: f32) {
        self.visual_weight = weight.clamp(0.0, 1.0);
    }

    pub fn set_wake_debounce_ms(&mut self, ms: u64) {
        self.wake_debounce_ms = ms;
    }

    pub fn interrupt_bus(&self) -> &InterruptBus {
        &self.interrupt_bus
    }

    pub fn reset_attention(&self) {
        self.set_attention_state(AttentionState::Idle);
    }

    fn set_attention_state(&self, state: AttentionState) {
        self.attention_state
            .store(state as u8, Ordering::Release);
    }

    fn should_debounce_wake(&self) -> bool {
        if let Ok(mut last_time) = self.last_wake_time.lock() {
            let now = current_time_ms();
            if now.saturating_sub(*last_time) < self.wake_debounce_ms {
                return true;
            }
            *last_time = now;
        }
        false
    }
}

impl Clone for PerceptualFunnel {
    fn clone(&self) -> Self {
        Self {
            interrupt_bus: self.interrupt_bus.clone(),
            attention_state: Arc::clone(&self.attention_state),
            voice_weight: self.voice_weight,
            visual_weight: self.visual_weight,
            last_wake_time: Arc::clone(&self.last_wake_time),
            wake_debounce_ms: self.wake_debounce_ms,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum AttentionState {
    Idle = 0,
    Attentive = 1,
    HighAlert = 2,
}

#[inline]
fn current_time_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::perception::interrupt_bus::{InterruptEvent, InterruptPriority, InterruptSource};

    #[test]
    fn test_evaluate_human_voice_triggers_wake() {
        let bus = InterruptBus::new(128);
        let funnel = PerceptualFunnel::new(bus);

        let event = InterruptEvent {
            priority: InterruptPriority::HumanVoice,
            source: InterruptSource::HumanInput,
            timestamp_ns: 0,
            context: "hello".to_string(),
        };

        let output = funnel.evaluate_attention(&event);
        assert!(matches!(
            output,
            PerceptualOutput::WakeCognitiveCore { .. }
        ));
        assert_eq!(funnel.current_attention_state(), AttentionState::HighAlert);
    }

    #[test]
    fn test_evaluate_critical_triggers_wake() {
        let bus = InterruptBus::new(128);
        let funnel = PerceptualFunnel::new(bus);

        let event = InterruptEvent {
            priority: InterruptPriority::Critical,
            source: InterruptSource::ExternalSignal,
            timestamp_ns: 0,
            context: "emergency".to_string(),
        };

        let output = funnel.evaluate_attention(&event);
        assert!(matches!(
            output,
            PerceptualOutput::WakeCognitiveCore { .. }
        ));
    }

    #[test]
    fn test_evaluate_low_priority_drops() {
        let bus = InterruptBus::new(128);
        let funnel = PerceptualFunnel::new(bus);

        let event = InterruptEvent {
            priority: InterruptPriority::Low,
            source: InterruptSource::SystemTimer,
            timestamp_ns: 0,
            context: "tick".to_string(),
        };

        let output = funnel.evaluate_attention(&event);
        assert!(matches!(output, PerceptualOutput::DropEvent));
    }

    #[test]
    fn test_process_interrupt_batch() {
        let bus = InterruptBus::new(128);
        let funnel = PerceptualFunnel::new(bus);

        let events = vec![
            InterruptEvent {
                priority: InterruptPriority::Low,
                source: InterruptSource::SystemTimer,
                timestamp_ns: 0,
                context: "a".to_string(),
            },
            InterruptEvent {
                priority: InterruptPriority::HumanVoice,
                source: InterruptSource::HumanInput,
                timestamp_ns: 0,
                context: "b".to_string(),
            },
        ];

        let outputs = funnel.process_interrupt_batch(events);
        assert_eq!(outputs.len(), 2);
        assert!(matches!(outputs[0], PerceptualOutput::DropEvent));
        assert!(matches!(outputs[1], PerceptualOutput::WakeCognitiveCore { .. }));
    }
}
