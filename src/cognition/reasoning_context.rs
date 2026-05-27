use crate::cognition::structured_intent::StructuredIntent;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

const MAX_CONTEXT_HISTORY: usize = 10;
const CONTEXT_TTL_MS: u64 = 60000;

#[derive(Debug, Clone)]
pub struct ReasoningContext {
    pub current_focus: Option<String>,
    pub focused_intent: Option<StructuredIntent>,
    pub history: Arc<Vec<StructuredIntent>>,
    pub last_valid_intent: Option<StructuredIntent>,
    pub context_hash: u64,
    pub created_at_ns: u64,
    pub last_updated_ns: u64,
}

impl ReasoningContext {
    pub fn new() -> Self {
        let now_ns = current_time_ns();
        Self {
            current_focus: None,
            focused_intent: None,
            history: Arc::new(Vec::new()),
            last_valid_intent: None,
            context_hash: 0,
            created_at_ns: now_ns,
            last_updated_ns: now_ns,
        }
    }

    pub fn update_focus(&mut self, focus: String, intent: StructuredIntent) {
        self.current_focus = Some(focus);
        self.focused_intent = Some(intent.clone());
        self.last_valid_intent = Some(intent);
        self.last_updated_ns = current_time_ns();
        self.recompute_hash();
    }

    pub fn add_to_history(&mut self, intent: StructuredIntent) {
        let mut history = (*self.history).clone();

        if history.len() >= MAX_CONTEXT_HISTORY {
            history.remove(0);
        }

        history.push(intent);
        self.history = Arc::new(history);
        self.last_updated_ns = current_time_ns();
    }

    pub fn expire_old_context(&mut self) {
        let now_ns = current_time_ns();
        let ttl_ns = CONTEXT_TTL_MS * 1_000_000;

        if now_ns.saturating_sub(self.last_updated_ns) > ttl_ns {
            self.clear_focus();
        }
    }

    pub fn clear_focus(&mut self) {
        self.current_focus = None;
        self.focused_intent = None;
        self.context_hash = 0;
        self.last_updated_ns = current_time_ns();
    }

    pub fn compute_context_hash(&self) -> u64 {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        if let Some(ref focus) = self.current_focus {
            hash ^= fnv_hash_str(focus);
            hash = hash.wrapping_mul(PRIME);
        }

        for intent in self.history.iter() {
            hash ^= intent.compute_intent_hash();
            hash = hash.wrapping_mul(PRIME);
        }

        hash
    }

    pub fn recompute_hash(&mut self) {
        self.context_hash = self.compute_context_hash();
    }

    pub fn get_history(&self) -> &[StructuredIntent] {
        self.history.as_ref()
    }

    pub fn age_ms(&self) -> u64 {
        let now_ns = current_time_ns();
        if now_ns > self.created_at_ns {
            (now_ns - self.created_at_ns) / 1_000_000
        } else {
            0
        }
    }

    pub fn is_expired(&self) -> bool {
        let now_ns = current_time_ns();
        let ttl_ns = CONTEXT_TTL_MS * 1_000_000;
        now_ns.saturating_sub(self.last_updated_ns) > ttl_ns
    }

    pub fn has_focus(&self) -> bool {
        self.current_focus.is_some() && self.focused_intent.is_some()
    }
}

impl Default for ReasoningContext {
    fn default() -> Self {
        Self::new()
    }
}

#[inline]
fn fnv_hash_str(s: &str) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    const PRIME: u64 = 0x100000001b3;

    for byte in s.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(PRIME);
    }

    hash
}

#[inline]
fn current_time_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cognition::structured_intent::IntentSource;

    #[test]
    fn test_reasoning_context_creation() {
        let ctx = ReasoningContext::new();
        assert!(!ctx.has_focus());
    }

    #[test]
    fn test_update_focus() {
        let mut ctx = ReasoningContext::new();
        let intent = StructuredIntent::new(
            "intent-001".to_string(),
            "search".to_string(),
            IntentSource::HumanVoice,
        );

        ctx.update_focus("searching".to_string(), intent);
        assert!(ctx.has_focus());
        assert_eq!(ctx.current_focus, Some("searching".to_string()));
    }

    #[test]
    fn test_add_to_history() {
        let mut ctx = ReasoningContext::new();

        for i in 0..15 {
            let intent = StructuredIntent::new(
                format!("intent-{:03}", i),
                "tool".to_string(),
                IntentSource::SystemTrigger,
            );
            ctx.add_to_history(intent);
        }

        assert_eq!(ctx.get_history().len(), MAX_CONTEXT_HISTORY);
    }

    #[test]
    fn test_compute_context_hash() {
        let mut ctx1 = ReasoningContext::new();
        let mut ctx2 = ReasoningContext::new();

        let intent = StructuredIntent::new(
            "test".to_string(),
            "tool".to_string(),
            IntentSource::HumanVoice,
        );

        ctx1.update_focus("focus".to_string(), intent.clone());
        ctx2.update_focus("focus".to_string(), intent);

        assert_eq!(ctx1.compute_context_hash(), ctx2.compute_context_hash());
    }

    #[test]
    fn test_expire_old_context() {
        let mut ctx = ReasoningContext::new();

        let intent = StructuredIntent::new(
            "test".to_string(),
            "tool".to_string(),
            IntentSource::HumanVoice,
        );

        ctx.update_focus("focus".to_string(), intent);
        assert!(ctx.has_focus());

        ctx.last_updated_ns = 0;
        ctx.expire_old_context();

        assert!(!ctx.has_focus());
    }
}
