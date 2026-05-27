use std::collections::HashMap;

const BLOCK_SIZE: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct BlockHash {
    hash: u64,
}

impl BlockHash {
    fn from_bytes(data: &[u8]) -> Self {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        for &byte in data.iter().take(BLOCK_SIZE) {
            hash ^= byte as u64;
            hash = hash.wrapping_mul(PRIME);
        }

        Self { hash }
    }

    pub fn value(&self) -> u64 {
        self.hash
    }
}

pub struct ScreenDeltaDetector {
    previous_hashes: HashMap<(usize, usize), BlockHash>,
    sensitivity_threshold: usize,
    width: usize,
    height: usize,
}

impl ScreenDeltaDetector {
    pub fn new(width: usize, height: usize, sensitivity_threshold: usize) -> Self {
        Self {
            previous_hashes: HashMap::new(),
            sensitivity_threshold,
            width,
            height,
        }
    }

    pub fn analyze_changes(&mut self, frame_data: &[u8]) -> ScreenDeltaAnalysis {
        let mut changed_blocks = Vec::new();
        let mut unchanged_blocks = 0;
        let block_cols = (self.width + BLOCK_SIZE - 1) / BLOCK_SIZE;
        let block_rows = (self.height + BLOCK_SIZE - 1) / BLOCK_SIZE;

        for block_row in 0..block_rows {
            for block_col in 0..block_cols {
                let block_hash = self.extract_block_hash(frame_data, block_row, block_col);
                let block_key = (block_row, block_col);

                let changed = if let Some(&prev_hash) = self.previous_hashes.get(&block_key) {
                    prev_hash != block_hash
                } else {
                    true
                };

                if changed {
                    changed_blocks.push(block_key);
                } else {
                    unchanged_blocks += 1;
                }

                self.previous_hashes.insert(block_key, block_hash);
            }
        }

        let change_ratio = if !changed_blocks.is_empty() {
            (changed_blocks.len() * 100) / (block_rows * block_cols)
        } else {
            0
        };

        ScreenDeltaAnalysis {
            changed_blocks,
            unchanged_blocks,
            change_ratio,
            is_significant: change_ratio >= self.sensitivity_threshold,
        }
    }

    pub fn perceptual_hash(&self, frame_data: &[u8]) -> u64 {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        let stride = if frame_data.len() > 1024 { 8 } else { 1 };
        for &byte in frame_data.iter().step_by(stride) {
            hash ^= byte as u64;
            hash = hash.wrapping_mul(PRIME);
        }

        hash
    }

    pub fn set_sensitivity(&mut self, threshold: usize) {
        self.sensitivity_threshold = threshold.clamp(1, 100);
    }

    pub fn clear_cache(&mut self) {
        self.previous_hashes.clear();
    }

    fn extract_block_hash(
        &self,
        frame_data: &[u8],
        block_row: usize,
        block_col: usize,
    ) -> BlockHash {
        let mut block_data = [0u8; BLOCK_SIZE];
        let mut idx = 0;

        let row_start = (block_row * BLOCK_SIZE).min(self.height);
        let col_start = (block_col * BLOCK_SIZE).min(self.width);
        let row_end = ((block_row + 1) * BLOCK_SIZE).min(self.height);
        let col_end = ((block_col + 1) * BLOCK_SIZE).min(self.width);

        for row in row_start..row_end {
            for col in col_start..col_end {
                let pixel_idx = (row * self.width + col) * 3;
                if pixel_idx + 2 < frame_data.len() && idx < BLOCK_SIZE {
                    let r = frame_data[pixel_idx];
                    let g = frame_data[pixel_idx + 1];
                    let b = frame_data[pixel_idx + 2];
                    block_data[idx] = ((r as u32 + g as u32 + b as u32) / 3) as u8;
                    idx += 1;
                }
            }
        }

        BlockHash::from_bytes(&block_data)
    }
}

#[derive(Debug)]
pub struct ScreenDeltaAnalysis {
    pub changed_blocks: Vec<(usize, usize)>,
    pub unchanged_blocks: usize,
    pub change_ratio: usize,
    pub is_significant: bool,
}

impl ScreenDeltaAnalysis {
    pub fn has_changes(&self) -> bool {
        !self.changed_blocks.is_empty()
    }

    pub fn changes_count(&self) -> usize {
        self.changed_blocks.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_hash_deterministic() {
        let data = [42u8; BLOCK_SIZE];
        let hash1 = BlockHash::from_bytes(&data);
        let hash2 = BlockHash::from_bytes(&data);
        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_block_hash_different() {
        let data1 = [42u8; BLOCK_SIZE];
        let data2 = [43u8; BLOCK_SIZE];
        let hash1 = BlockHash::from_bytes(&data1);
        let hash2 = BlockHash::from_bytes(&data2);
        assert_ne!(hash1, hash2);
    }

    #[test]
    fn test_screen_delta_detector_no_change() {
        let mut detector = ScreenDeltaDetector::new(640, 480, 5);
        let frame = vec![128u8; 640 * 480 * 3];

        let _analysis1 = detector.analyze_changes(&frame);
        let analysis2 = detector.analyze_changes(&frame);

        assert!(!analysis2.has_changes());
    }

    #[test]
    fn test_screen_delta_detector_with_change() {
        let mut detector = ScreenDeltaDetector::new(640, 480, 5);
        let frame1 = vec![128u8; 640 * 480 * 3];
        let mut frame2 = frame1.clone();

        detector.analyze_changes(&frame1);

        let change_size = (640 * 480 * 3) / 10;
        frame2[0..change_size].iter_mut().for_each(|b| *b = 200);

        let analysis = detector.analyze_changes(&frame2);
        assert!(analysis.has_changes());
        assert!(analysis.change_ratio > 0);
    }

    #[test]
    fn test_perceptual_hash() {
        let detector = ScreenDeltaDetector::new(640, 480, 5);
        let frame1 = vec![128u8; 1000];
        let frame2 = vec![200u8; 1000];

        let hash1 = detector.perceptual_hash(&frame1);
        let hash2 = detector.perceptual_hash(&frame2);

        assert_ne!(hash1, hash2);
    }
}
