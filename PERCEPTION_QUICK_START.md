PERCEPTION LAYER QUICK REFERENCE

=== MODULE EXPORTS (src/lib.rs) ===

use sexta_feira_perception::{
    // Interrupt bus
    InterruptBus, InterruptEvent, InterruptPriority, InterruptSource,
    
    // Audio
    AudioRingBuffer,
    
    // Voice
    VoiceGate, VoiceGateState,
    
    // Visual
    ScreenDeltaDetector, ScreenDeltaAnalysis, BlockHash,
    
    // Perception
    PerceptualFunnel, PerceptualOutput, AttentionState,
    
    // Context
    CognitiveSnapshot, CognitiveContext, WindowState, WindowBounds,
    ToolState, ToolStatus, SymbolicMarker,
};

=== QUICK START ===

Step 1: Initialize components

let bus = InterruptBus::new(256);
let buffer = AudioRingBuffer::with_capacity(16, 512);
let mut gate = VoiceGate::default_threshold();
let mut detector = ScreenDeltaDetector::new(640, 480, 5);
let funnel = PerceptualFunnel::new(bus.clone());

Step 2: Process audio stream

let audio_frame = [0.0f32; 512]; // from audio device
buffer.push_samples(&audio_frame);
let state = gate.process_audio_frame(&audio_frame);

if state == VoiceGateState::VoiceDetected {
    bus.trigger_human_voice("speech".into());
}

Step 3: Process video stream

let video_frame = vec![128u8; 640 * 480 * 3]; // RGB24
let analysis = detector.analyze_changes(&video_frame);

if analysis.is_significant {
    bus.trigger_screen_delta(format!("changes: {}", analysis.changes_count()));
}

Step 4: Evaluate attention

let mut rx = bus.subscribe();
while let Ok(event) = rx.recv().await {
    match funnel.evaluate_attention(&event) {
        PerceptualOutput::WakeCognitiveCore { context_trigger } => {
            println!("WAKE: {}", context_trigger);
            // Trigger kernel
        }
        _ => {
            // Idle or dropped
        }
    }
}

Step 5: Create execution context

let mut snapshot = CognitiveSnapshot::new("conv-001".into())
    .with_intent("find_files".into());

snapshot.set_focus_hash(1234567890);
snapshot.add_metadata("user_id".into(), "alice".into());

let tool = ToolState {
    name: "file_search".into(),
    status: ToolStatus::Executing,
    input_hash: 111,
    output_hash: 222,
    duration_ns: 1_000_000,
    invocation_count: 1,
};
snapshot.add_tool_state(tool);

=== PERFORMANCE TIPS ===

1. Audio buffer sizing
   - For 48kHz: 16 frames × 512 samples = 32KB
   - Adjust based on latency budget
   buffer = AudioRingBuffer::with_capacity(16, 512);

2. Voice gate tuning
   - Decrease energy_threshold for sensitive pickup
   - Increase zero_crossing_threshold for noise rejection
   gate.set_energy_threshold(0.01);
   gate.set_zero_crossing_threshold(20);

3. Visual detection sensitivity
   - Lower threshold (1%) = more wakes, more CPU
   - Higher threshold (50%) = fewer false positives, may miss changes
   detector.set_sensitivity(10);

4. Interrupt bus capacity
   - Allocate conservatively: typical usage ~50 events/sec
   - Exceeding capacity drops oldest events
   bus = InterruptBus::new(256); // ~5 second window

5. Debouncing visual interrupts
   - Prevent visual noise from flooding kernel
   funnel.set_wake_debounce_ms(500);

=== COMMON PATTERNS ===

Pattern: Manual interrupt triggering

let event = InterruptEvent {
    priority: InterruptPriority::Critical,
    source: InterruptSource::ExternalSignal,
    timestamp_ns: std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos() as u64,
    context: "emergency_stop".into(),
};
bus.trigger(event);

Pattern: Batch event processing

let events = vec![
    InterruptEvent { /* ... */ },
    InterruptEvent { /* ... */ },
];

let outputs = funnel.process_interrupt_batch(events);
for (event, output) in events.iter().zip(outputs.iter()) {
    // Handle each
}

Pattern: TTL-based markers

let marker = SymbolicMarker::new(
    "current_task".into(),
    "file_browser".into(),
    0.95,
)
.with_ttl(10000); // 10 seconds

snapshot.add_symbolic_marker(marker);

// Later...
snapshot.cleanup_expired_markers();

Pattern: Tool execution tracking

let mut tool_state = ToolState {
    name: tool_name.into(),
    status: ToolStatus::Ready,
    input_hash: hash_input(&args),
    output_hash: 0,
    duration_ns: 0,
    invocation_count: 0,
};

let start = std::time::Instant::now();
let result = execute_tool(&args).await;
tool_state.duration_ns = start.elapsed().as_nanos() as u64;
tool_state.status = ToolStatus::Completed;
tool_state.output_hash = hash_output(&result);

snapshot.add_tool_state(tool_state);

Pattern: Window state tracking

let window = WindowState {
    window_id: 0x7f1234567890,
    title: "Editor".into(),
    bounds: WindowBounds {
        x: 100,
        y: 100,
        width: 800,
        height: 600,
    },
    is_focused: true,
};

let mut snapshot = snapshot.with_window(window);

=== TESTING ===

Run unit tests:
cargo test --lib

Run specific test:
cargo test perception::voice_gate::tests::test_voice_gate_detection

Run with backtrace:
RUST_BACKTRACE=1 cargo test --lib

=== THREAD SAFETY ===

All components are Send + Sync:

- InterruptBus: Arc<broadcast::Sender> → Send + Sync
- AudioRingBuffer: Arc<UnsafeCell> + Arc<AtomicUsize> → Send + Sync
- VoiceGate: Arc<AtomicU8> → Send + Sync
- ScreenDeltaDetector: owned HashMap → Send (not Sync, use Mutex if shared)
- PerceptualFunnel: Arc-based state → Send + Sync
- CognitiveSnapshot: Arc collections → Send + Sync

Shared detector across threads:
use parking_lot::Mutex;

let detector = Mutex::new(ScreenDeltaDetector::new(640, 480, 5));
let detector = Arc::new(detector);

// In worker thread:
let analysis = detector.lock().analyze_changes(&frame);

=== ERROR HANDLING ===

Audio buffer write (infallible):
buffer.push_samples(&samples); // Always succeeds

Voice gate processing (infallible):
let state = gate.process_audio_frame(&frame); // Returns state

Visual analysis (infallible):
let analysis = detector.analyze_changes(&frame); // Returns analysis

Interrupt triggering (fallible if broadcast full):
bus.trigger(event); // Silent drop if capacity exceeded, check with:
if bus.receiver_count() == 0 { /* no listeners */ }

Snapshot operations (all owned):
snapshot.add_tool_state(tool); // Consumes tool
snapshot.add_symbolic_marker(marker); // Consumes marker

=== DEBUGGING ===

Interrupt bus diagnostics:
println!("Interrupt count: {}", bus.interrupt_count());
println!("Active receivers: {}", bus.receiver_count());

Audio buffer diagnostics:
println!("Write position: {}", buffer.current_write_position());
println!("Total samples: {}", buffer.total_samples_written());

Voice gate diagnostics:
println!("State: {:?}", gate.current_state());
println!("Is voice: {}", gate.is_voice_detected());

Visual detection diagnostics:
println!("Changed blocks: {}", analysis.changes_count());
println!("Change ratio: {}%", analysis.change_ratio);

Snapshot diagnostics:
println!("Age: {}ms", snapshot.age_ms());
println!("Hash: {}", snapshot.compute_snapshot_hash());
println!("Tools: {}", snapshot.tool_states.len());
println!("Markers: {}", snapshot.symbolic_markers.len());

=== COMPILE FLAGS ===

Debug (dev profile):
- opt-level = 0
- Full symbols
- Run time: ~2x slower
- Binary size: ~5MB

Release (prod profile):
- opt-level = 3
- LTO enabled
- Code gen units = 1
- Strip symbols
- Run time: ~2x faster
- Binary size: ~500KB

Enable SIMD (future):
RUSTFLAGS="-C target-feature=+avx2" cargo build --release

=== INTEGRATION WITH BACKEND-CORE ===

From Python FastAPI, call Rust via:

1. PyO3 wrapper (future):
   #[pyfunction]
   fn process_audio_frame(buffer: &AudioRingBuffer, frame: Vec<f32>) -> bool {
       buffer.push_samples(&frame);
       // ...
   }

2. Or use as external service (recommended):
   - Rust perception as daemon
   - FastAPI calls via REST or gRPC
   - Rust service owns all sensory state
   - Python kernel calls perception daemon for decisions

3. Or compile as C library:
   rustc --crate-type cdylib target...
   // Link from Python via ctypes

=== ROADMAP ===

Phase 2 (CURRENT): Perception layer
- [x] Interrupt bus
- [x] Audio ringbuffer
- [x] Voice gate
- [x] Screen delta
- [x] Perceptual funnel
- [x] Cognitive snapshot
- [x] Unit tests (23 passing)
- [x] Release build optimization

Phase 3: Kernel integration
- [ ] Capability matrix validator
- [ ] Event broker middleware
- [ ] Task dispatcher
- [ ] Memory arena allocator

Phase 4: Android support
- [ ] JNI bindings
- [ ] Android runtime adaptation
- [ ] Sensor HAL integration
- [ ] Latency profiling on device

Phase 5: Neuro-symbolic reasoning
- [ ] Temporal constraint solver
- [ ] Multi-hypothesis reasoning
- [ ] Causal inference
- [ ] Abductive planning
