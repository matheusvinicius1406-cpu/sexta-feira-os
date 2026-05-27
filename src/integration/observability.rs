use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

pub type TraceResult<T> = Result<T, TraceError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TraceError {
    InvalidSpan,
    SpanAlreadyClosed,
    BufferFull,
}

#[derive(Debug, Clone)]
pub struct TraceSpan {
    pub name: String,
    pub start_ns: u64,
    pub end_ns: u64,
    pub duration_ns: u64,
}

pub struct RuntimeMetrics {
    pub total_requests: Arc<AtomicU64>,
    pub requests_succeeded: Arc<AtomicU64>,
    pub requests_failed: Arc<AtomicU64>,
    pub total_latency_ns: Arc<AtomicU64>,
    pub interrupt_count: Arc<AtomicU64>,
    pub perception_events: Arc<AtomicU64>,
    pub cognitive_decisions: Arc<AtomicU64>,
    pub tool_executions: Arc<AtomicU64>,
}

impl RuntimeMetrics {
    pub fn new() -> Self {
        Self {
            total_requests: Arc::new(AtomicU64::new(0)),
            requests_succeeded: Arc::new(AtomicU64::new(0)),
            requests_failed: Arc::new(AtomicU64::new(0)),
            total_latency_ns: Arc::new(AtomicU64::new(0)),
            interrupt_count: Arc::new(AtomicU64::new(0)),
            perception_events: Arc::new(AtomicU64::new(0)),
            cognitive_decisions: Arc::new(AtomicU64::new(0)),
            tool_executions: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn record_request_start(&self) {
        self.total_requests.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_request_success(&self, duration_ns: u64) {
        self.requests_succeeded.fetch_add(1, Ordering::Relaxed);
        self.total_latency_ns
            .fetch_add(duration_ns, Ordering::Relaxed);
    }

    pub fn record_request_failure(&self) {
        self.requests_failed.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_interrupt(&self) {
        self.interrupt_count.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_perception_event(&self) {
        self.perception_events.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_cognitive_decision(&self) {
        self.cognitive_decisions.fetch_add(1, Ordering::Relaxed);
    }

    pub fn record_tool_execution(&self) {
        self.tool_executions.fetch_add(1, Ordering::Relaxed);
    }

    pub fn get_snapshot(&self) -> RuntimeMetricsSnapshot {
        let total = self.total_requests.load(Ordering::Acquire);
        let succeeded = self.requests_succeeded.load(Ordering::Acquire);
        let failed = self.requests_failed.load(Ordering::Acquire);
        let total_latency_ns = self.total_latency_ns.load(Ordering::Acquire);

        let avg_latency_ns = if succeeded > 0 {
            total_latency_ns / succeeded
        } else {
            0
        };

        RuntimeMetricsSnapshot {
            total_requests: total,
            succeeded_requests: succeeded,
            failed_requests: failed,
            average_latency_ns: avg_latency_ns,
            interrupt_count: self.interrupt_count.load(Ordering::Acquire),
            perception_events: self.perception_events.load(Ordering::Acquire),
            cognitive_decisions: self.cognitive_decisions.load(Ordering::Acquire),
            tool_executions: self.tool_executions.load(Ordering::Acquire),
        }
    }
}

impl Clone for RuntimeMetrics {
    fn clone(&self) -> Self {
        Self {
            total_requests: Arc::clone(&self.total_requests),
            requests_succeeded: Arc::clone(&self.requests_succeeded),
            requests_failed: Arc::clone(&self.requests_failed),
            total_latency_ns: Arc::clone(&self.total_latency_ns),
            interrupt_count: Arc::clone(&self.interrupt_count),
            perception_events: Arc::clone(&self.perception_events),
            cognitive_decisions: Arc::clone(&self.cognitive_decisions),
            tool_executions: Arc::clone(&self.tool_executions),
        }
    }
}

impl Default for RuntimeMetrics {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone)]
pub struct RuntimeMetricsSnapshot {
    pub total_requests: u64,
    pub succeeded_requests: u64,
    pub failed_requests: u64,
    pub average_latency_ns: u64,
    pub interrupt_count: u64,
    pub perception_events: u64,
    pub cognitive_decisions: u64,
    pub tool_executions: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_creation() {
        let metrics = RuntimeMetrics::new();
        let snapshot = metrics.get_snapshot();

        assert_eq!(snapshot.total_requests, 0);
        assert_eq!(snapshot.succeeded_requests, 0);
    }

    #[test]
    fn test_record_request() {
        let metrics = RuntimeMetrics::new();

        metrics.record_request_start();
        metrics.record_request_success(1_000_000);

        let snapshot = metrics.get_snapshot();
        assert_eq!(snapshot.total_requests, 1);
        assert_eq!(snapshot.succeeded_requests, 1);
    }

    #[test]
    fn test_record_interrupt() {
        let metrics = RuntimeMetrics::new();

        metrics.record_interrupt();
        metrics.record_interrupt();

        let snapshot = metrics.get_snapshot();
        assert_eq!(snapshot.interrupt_count, 2);
    }

    #[test]
    fn test_average_latency() {
        let metrics = RuntimeMetrics::new();

        metrics.record_request_start();
        metrics.record_request_success(1_000_000);
        metrics.record_request_start();
        metrics.record_request_success(3_000_000);

        let snapshot = metrics.get_snapshot();
        assert_eq!(snapshot.average_latency_ns, 2_000_000);
    }
}
