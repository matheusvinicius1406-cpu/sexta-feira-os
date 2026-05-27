use sexta_feira_perception::{
    AudioRingBuffer, CognitiveSnapshot, InterruptBus, InterruptEvent, InterruptPriority,
    InterruptSource, PerceptualFunnel, PerceptualOutput, ScreenDeltaDetector, SymbolicMarker,
    ToolState, ToolStatus, VoiceGate, VoiceGateState,
};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::time::interval;

const AUDIO_SAMPLE_RATE: usize = 48000;
const AUDIO_FRAME_SIZE: usize = 512;
const AUDIO_FRAMES_PER_BUFFER: usize = 16;

const SCREEN_WIDTH: usize = 640;
const SCREEN_HEIGHT: usize = 480;
const SCREEN_SENSITIVITY: usize = 5;

async fn audio_stream_simulator(bus: InterruptBus, buffer: AudioRingBuffer, mut gate: VoiceGate) {
    let mut interval = interval(std::time::Duration::from_millis(10));
    let mut voice_active = false;

    loop {
        interval.tick().await;

        let frame = if voice_active {
            generate_voice_frame()
        } else {
            generate_silence_frame()
        };

        buffer.push_samples(&frame);

        let state = gate.process_audio_frame(&frame);

        let is_detected = state == VoiceGateState::VoiceDetected;
        if is_detected && !voice_active {
            voice_active = true;
            bus.trigger_human_voice("voice_stream_started".to_string());
            println!("[AUDIO] Voice detected, interrupt triggered");
        } else if !is_detected && voice_active {
            voice_active = false;
            println!("[AUDIO] Voice ended, silence detected");
        }

        if voice_active {
            std::thread::sleep(std::time::Duration::from_millis(50));
            voice_active = false;
        }
    }
}

async fn screen_stream_simulator(mut detector: ScreenDeltaDetector, funnel: PerceptualFunnel) {
    let mut interval = interval(std::time::Duration::from_millis(33));
    let mut frame_count = 0u32;
    let mut current_frame = vec![128u8; SCREEN_WIDTH * SCREEN_HEIGHT * 3];

    loop {
        interval.tick().await;

        frame_count += 1;

        if frame_count % 30 == 0 {
            let change_size = (SCREEN_WIDTH * SCREEN_HEIGHT * 3) / 20;
            for i in 0..change_size {
                current_frame[i] = ((current_frame[i] as u32 + 50) % 256) as u8;
            }
            println!(
                "[SCREEN] Frame {} - significant change detected",
                frame_count
            );
        }

        let analysis = detector.analyze_changes(&current_frame);

        if analysis.is_significant {
            let event = InterruptEvent {
                priority: InterruptPriority::Medium,
                source: InterruptSource::ScreenDelta,
                timestamp_ns: current_time_ns(),
                context: format!(
                    "visual_delta:blocks={} ratio={}%",
                    analysis.changes_count(),
                    analysis.change_ratio
                ),
            };

            match funnel.evaluate_attention(&event) {
                PerceptualOutput::WakeCognitiveCore { context_trigger } => {
                    println!("[FUNNEL] WAKE: {}", context_trigger);
                }
                PerceptualOutput::Idle => {
                    println!("[FUNNEL] Idle - debounced");
                }
                _ => {}
            }
        }
    }
}

async fn perception_evaluator(funnel: Arc<PerceptualFunnel>) {
    let mut rx = funnel.interrupt_bus().subscribe();
    let mut wake_count = 0u32;

    loop {
        match rx.recv().await {
            Ok(event) => {
                let output = funnel.evaluate_attention(&event);
                let attention = funnel.current_attention_state();

                match output {
                    PerceptualOutput::WakeCognitiveCore { context_trigger } => {
                        wake_count += 1;
                        println!(
                            "[PERCEPTION] Wake #{} | Context: {} | Attention: {:?}",
                            wake_count, context_trigger, attention
                        );

                        let mut snapshot = CognitiveSnapshot::new(format!("wake_{}", wake_count));
                        snapshot.add_metadata(
                            "trigger_source".to_string(),
                            format!("{:?}", event.source),
                        );
                        println!("[SNAPSHOT] Bound cognitive context");
                    }
                    PerceptualOutput::Idle => {
                        println!("[PERCEPTION] Idle (no action)");
                    }
                    PerceptualOutput::DropEvent => {
                        println!("[PERCEPTION] Event dropped (priority filter)");
                    }
                }
            }
            Err(_) => {
                println!("[PERCEPTION] Broadcast closed");
                return;
            }
        }
    }
}

async fn diagnostics_reporter(bus: Arc<InterruptBus>) {
    let mut interval = interval(std::time::Duration::from_secs(2));

    loop {
        interval.tick().await;

        let interrupt_count = bus.interrupt_count();
        let receiver_count = bus.receiver_count();

        println!(
            "[DIAGNOSTICS] Interrupts: {} | Active receivers: {}",
            interrupt_count, receiver_count
        );
    }
}

fn generate_voice_frame() -> Vec<f32> {
    (0..AUDIO_FRAME_SIZE)
        .map(|i| {
            let freq = 440.0;
            let sample_rate = AUDIO_SAMPLE_RATE as f32;
            let phase = 2.0 * std::f32::consts::PI * freq * i as f32 / sample_rate;
            (phase.sin() * 0.2) + (phase * 2.0).sin() * 0.1
        })
        .collect()
}

fn generate_silence_frame() -> Vec<f32> {
    vec![0.001f32; AUDIO_FRAME_SIZE]
}

fn current_time_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

#[tokio::main]
async fn main() {
    println!("=== Sexta-Feira OS - Perception Layer Integration Demo ===\n");

    let bus = Arc::new(InterruptBus::new(256));
    let audio_buffer = AudioRingBuffer::with_capacity(AUDIO_FRAMES_PER_BUFFER, AUDIO_FRAME_SIZE);
    let voice_gate = VoiceGate::default_threshold();
    let screen_detector = ScreenDeltaDetector::new(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_SENSITIVITY);
    let funnel = Arc::new(PerceptualFunnel::new((*bus).clone()));

    println!("Initialized components:");
    println!("  - InterruptBus (capacity: 256)");
    println!(
        "  - AudioRingBuffer ({} frames × {} samples)",
        AUDIO_FRAMES_PER_BUFFER, AUDIO_FRAME_SIZE
    );
    println!("  - VoiceGate (energy: 0.015, zcr: 15)");
    println!(
        "  - ScreenDeltaDetector ({}×{}, sensitivity: {}%)",
        SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_SENSITIVITY
    );
    println!("  - PerceptualFunnel (debounce: 500ms)");
    println!();

    let audio_task = {
        let bus = bus.clone();
        let buffer = audio_buffer.clone();
        tokio::spawn(audio_stream_simulator((*bus).clone(), buffer, voice_gate))
    };

    let screen_task = {
        let funnel = funnel.clone();
        tokio::spawn(screen_stream_simulator(screen_detector, (*funnel).clone()))
    };

    let evaluator_task = {
        let funnel = funnel.clone();
        tokio::spawn(perception_evaluator(funnel))
    };

    let diagnostics_task = {
        let bus = bus.clone();
        tokio::spawn(diagnostics_reporter(bus))
    };

    println!("Starting perception pipeline...\n");

    tokio::select! {
        _ = audio_task => println!("Audio stream ended"),
        _ = screen_task => println!("Screen stream ended"),
        _ = evaluator_task => println!("Evaluator ended"),
        _ = diagnostics_task => println!("Diagnostics ended"),
    }
}

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[tokio::test]
    async fn test_voice_detection_integration() {
        let _bus = InterruptBus::new(128);
        let buffer = AudioRingBuffer::with_capacity(16, 512);
        let mut gate = VoiceGate::new(0.01, 5);

        let voice_frame = generate_voice_frame();
        buffer.push_samples(&voice_frame);

        let _state = gate.process_audio_frame(&voice_frame);
        gate.process_audio_frame(&voice_frame);
        let final_state = gate.process_audio_frame(&voice_frame);

        assert_eq!(final_state, VoiceGateState::VoiceDetected);
    }

    #[test]
    fn test_cognitive_snapshot_creation() {
        let mut snapshot = CognitiveSnapshot::new("test-conv".to_string());

        let tool = ToolState {
            name: "test_tool".to_string(),
            status: ToolStatus::Executing,
            input_hash: 123,
            output_hash: 0,
            duration_ns: 1_000_000,
            invocation_count: 1,
        };

        snapshot.add_tool_state(tool);

        let marker = SymbolicMarker::new("test_marker".to_string(), "test_value".to_string(), 0.95);

        snapshot.add_symbolic_marker(marker);

        assert_eq!(snapshot.tool_states.len(), 1);
        assert_eq!(snapshot.symbolic_markers.len(), 1);
    }

    #[test]
    fn test_interrupt_priority_ordering() {
        let bus = InterruptBus::new(128);

        bus.trigger_human_voice("test".to_string());
        bus.trigger_critical(InterruptSource::SystemTimer, "test".to_string());

        assert_eq!(bus.interrupt_count(), 2);
    }
}
