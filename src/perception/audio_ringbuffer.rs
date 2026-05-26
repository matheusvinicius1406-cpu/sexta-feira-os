use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::cell::UnsafeCell;

pub struct AudioRingBuffer {
    data: Arc<UnsafeCell<Vec<f32>>>,
    write_index: Arc<AtomicUsize>,
    capacity: usize,
    frame_size: usize,
    buffer_size: usize,
}

impl AudioRingBuffer {
    pub fn with_capacity(capacity: usize, frame_size: usize) -> Self {
        let total_samples = capacity * frame_size;
        Self {
            data: Arc::new(UnsafeCell::new(vec![0.0f32; total_samples])),
            write_index: Arc::new(AtomicUsize::new(0)),
            capacity,
            frame_size,
            buffer_size: total_samples,
        }
    }

    pub fn push_samples(&self, samples: &[f32]) {
        let mut write_idx = self.write_index.load(Ordering::Acquire);

        unsafe {
            let data = &mut *self.data.get();
            for sample in samples {
                data[write_idx] = *sample;
                write_idx = (write_idx + 1) % self.buffer_size;
            }
        }

        self.write_index.store(write_idx, Ordering::Release);
    }

    pub fn get_latest_frame(&self) -> Vec<f32> {
        let write_idx = self.write_index.load(Ordering::Acquire);
        let mut frame = vec![0.0f32; self.frame_size];

        let start_idx = if write_idx >= self.frame_size {
            write_idx - self.frame_size
        } else {
            let wrapped = self.buffer_size - (self.frame_size - write_idx);
            wrapped % self.buffer_size
        };

        unsafe {
            let data = &*self.data.get();
            if start_idx + self.frame_size <= data.len() {
                frame.copy_from_slice(&data[start_idx..start_idx + self.frame_size]);
            } else {
                let first_part = data.len() - start_idx;
                let second_part = self.frame_size - first_part;
                frame[..first_part].copy_from_slice(&data[start_idx..]);
                frame[first_part..].copy_from_slice(&data[..second_part]);
            }
        }

        frame
    }

    pub fn get_latest_frames(&self, num_frames: usize) -> Vec<f32> {
        let write_idx = self.write_index.load(Ordering::Acquire);
        let total_samples = num_frames * self.frame_size;
        let mut result = vec![0.0f32; total_samples];

        let start_idx = if write_idx >= total_samples {
            write_idx - total_samples
        } else {
            let wrapped = self.buffer_size - (total_samples - write_idx);
            wrapped % self.buffer_size
        };

        unsafe {
            let data = &*self.data.get();
            if start_idx + total_samples <= data.len() {
                result.copy_from_slice(&data[start_idx..start_idx + total_samples]);
            } else {
                let first_part = data.len() - start_idx;
                let second_part = total_samples - first_part;
                result[..first_part].copy_from_slice(&data[start_idx..]);
                result[first_part..].copy_from_slice(&data[..second_part]);
            }
        }

        result
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn frame_size(&self) -> usize {
        self.frame_size
    }

    pub fn total_samples_written(&self) -> usize {
        self.write_index.load(Ordering::Acquire)
    }

    pub fn current_write_position(&self) -> usize {
        self.write_index.load(Ordering::Acquire) % self.buffer_size
    }
}

impl Clone for AudioRingBuffer {
    fn clone(&self) -> Self {
        Self {
            data: Arc::clone(&self.data),
            write_index: Arc::clone(&self.write_index),
            capacity: self.capacity,
            frame_size: self.frame_size,
            buffer_size: self.buffer_size,
        }
    }
}

unsafe impl Send for AudioRingBuffer {}
unsafe impl Sync for AudioRingBuffer {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_ringbuffer_push_and_get() {
        let buffer = AudioRingBuffer::with_capacity(16, 512);
        let samples = vec![0.1f32; 512];

        buffer.push_samples(&samples);
        let frame = buffer.get_latest_frame();

        assert_eq!(frame.len(), 512);
        assert!(frame.iter().all(|&s| (s - 0.1).abs() < 0.001));
    }

    #[test]
    fn test_audio_ringbuffer_wraparound() {
        let buffer = AudioRingBuffer::with_capacity(4, 100);
        let samples1 = vec![0.1f32; 100];
        let samples2 = vec![0.2f32; 100];

        buffer.push_samples(&samples1);
        buffer.push_samples(&samples2);
        buffer.push_samples(&samples1);
        buffer.push_samples(&samples2);

        let frame = buffer.get_latest_frame();
        assert_eq!(frame.len(), 100);
        assert!(frame.iter().all(|&s| (s - 0.2).abs() < 0.001));
    }

    #[test]
    fn test_get_multiple_frames() {
        let buffer = AudioRingBuffer::with_capacity(16, 256);
        for i in 0..5 {
            let samples = vec![i as f32 / 10.0; 256];
            buffer.push_samples(&samples);
        }

        let frames = buffer.get_latest_frames(3);
        assert_eq!(frames.len(), 768);
    }
}
