use std::sync::atomic::{AtomicU8, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VoiceGateState {
    Silence,
    VoiceDetected,
}

pub struct VoiceGate {
    state: Arc<AtomicU8>,
    energy_threshold: f32,
    zero_crossing_threshold: u32,
    frame_count: u32,
    voice_frames_required: u32,
    silence_frames_required: u32,
    frame_counter: u32,
}

impl VoiceGate {
    pub fn new(energy_threshold: f32, zero_crossing_threshold: u32) -> Self {
        Self {
            state: Arc::new(AtomicU8::new(VoiceGateState::Silence as u8)),
            energy_threshold,
            zero_crossing_threshold,
            frame_count: 0,
            voice_frames_required: 2,
            silence_frames_required: 8,
            frame_counter: 0,
        }
    }

    pub fn default_threshold() -> Self {
        Self::new(0.015, 15)
    }

    pub fn process_audio_frame(&mut self, samples: &[f32]) -> VoiceGateState {
        let energy = calculate_frame_energy(samples);
        let zero_crossings = count_zero_crossings(samples);

        let is_voice = energy > self.energy_threshold 
            && zero_crossings >= self.zero_crossing_threshold;

        let current_state = self.current_state();

        self.frame_counter += 1;

        let new_state = match (current_state, is_voice) {
            (VoiceGateState::Silence, true) => {
                if self.frame_counter >= self.voice_frames_required {
                    self.frame_counter = 0;
                    VoiceGateState::VoiceDetected
                } else {
                    VoiceGateState::Silence
                }
            }
            (VoiceGateState::VoiceDetected, false) => {
                if self.frame_counter >= self.silence_frames_required {
                    self.frame_counter = 0;
                    VoiceGateState::Silence
                } else {
                    VoiceGateState::VoiceDetected
                }
            }
            _ => {
                if is_voice {
                    self.frame_counter = self.frame_counter.saturating_add(1);
                } else {
                    self.frame_counter = 0;
                }
                current_state
            }
        };

        self.state.store(new_state as u8, Ordering::Release);
        new_state
    }

    pub fn current_state(&self) -> VoiceGateState {
        let state_byte = self.state.load(Ordering::Acquire);
        if state_byte == 0 {
            VoiceGateState::Silence
        } else {
            VoiceGateState::VoiceDetected
        }
    }

    pub fn is_voice_detected(&self) -> bool {
        self.current_state() == VoiceGateState::VoiceDetected
    }

    pub fn set_energy_threshold(&mut self, threshold: f32) {
        self.energy_threshold = threshold;
    }

    pub fn set_zero_crossing_threshold(&mut self, threshold: u32) {
        self.zero_crossing_threshold = threshold;
    }

    pub fn set_voice_frames_required(&mut self, frames: u32) {
        self.voice_frames_required = frames;
    }

    pub fn set_silence_frames_required(&mut self, frames: u32) {
        self.silence_frames_required = frames;
    }

    pub fn reset(&mut self) {
        self.frame_counter = 0;
        self.state.store(VoiceGateState::Silence as u8, Ordering::Release);
    }
}

impl Clone for VoiceGate {
    fn clone(&self) -> Self {
        Self {
            state: Arc::clone(&self.state),
            energy_threshold: self.energy_threshold,
            zero_crossing_threshold: self.zero_crossing_threshold,
            frame_count: self.frame_count,
            voice_frames_required: self.voice_frames_required,
            silence_frames_required: self.silence_frames_required,
            frame_counter: self.frame_counter,
        }
    }
}

#[inline]
fn calculate_frame_energy(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return 0.0;
    }

    let sum: f32 = samples.iter().map(|s| s * s).sum();
    (sum / samples.len() as f32).sqrt()
}

#[inline]
fn count_zero_crossings(samples: &[f32]) -> u32 {
    if samples.len() < 2 {
        return 0;
    }

    let mut crossings = 0u32;
    for i in 1..samples.len() {
        if (samples[i] >= 0.0 && samples[i - 1] < 0.0)
            || (samples[i] < 0.0 && samples[i - 1] >= 0.0)
        {
            crossings += 1;
        }
    }
    crossings
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_voice_gate_silence() {
        let mut gate = VoiceGate::new(0.1, 20);
        let silent_samples = vec![0.001f32; 512];

        for _ in 0..10 {
            gate.process_audio_frame(&silent_samples);
        }

        assert_eq!(gate.current_state(), VoiceGateState::Silence);
    }

    #[test]
    fn test_voice_gate_detection() {
        let mut gate = VoiceGate::new(0.01, 5);
        let voice_samples = generate_voice_like_samples(0.1, 512);

        let _state1 = gate.process_audio_frame(&voice_samples);
        let _state2 = gate.process_audio_frame(&voice_samples);
        let state3 = gate.process_audio_frame(&voice_samples);

        assert_eq!(state3, VoiceGateState::VoiceDetected);
    }

    #[test]
    fn test_zero_crossing_count() {
        let samples = vec![-0.1, 0.1, -0.1, 0.1, -0.1];
        let crossings = count_zero_crossings(&samples);
        assert_eq!(crossings, 4);
    }

    fn generate_voice_like_samples(amplitude: f32, count: usize) -> Vec<f32> {
        (0..count)
            .map(|i| {
                let freq = 440.0;
                let phase = 2.0 * std::f32::consts::PI * freq * i as f32 / 48000.0;
                (phase.sin() * amplitude) + (phase * 2.0).sin() * 0.3 * amplitude
            })
            .collect()
    }
}
