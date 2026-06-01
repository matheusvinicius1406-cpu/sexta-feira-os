use crate::cognition::cognitive_errors::{CognitiveError, CognitiveResult};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

#[derive(Debug, Clone)]
pub struct CognitiveBudget {
    pub max_execution_time_ms: u64,
    pub max_memory_bytes: u64,
    pub max_reasoning_depth: u32,
}

impl CognitiveBudget {
    pub fn realtime() -> Self {
        Self {
            max_execution_time_ms: 500,
            max_memory_bytes: 50 * 1024 * 1024,
            max_reasoning_depth: 50,
        }
    }
}

impl Default for CognitiveBudget {
    fn default() -> Self {
        Self {
            max_execution_time_ms: 5000,
            max_memory_bytes: 100 * 1024 * 1024,
            max_reasoning_depth: 100,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SchedulerDecision {
    Allow,
    Deny,
    TimeoutImminent,
    BudgetExceeded,
}

pub struct ExecutionPermit {
    start_time: Instant,
    max_duration_ms: u64,
    should_preempt: Arc<AtomicBool>,
}

impl ExecutionPermit {
    pub fn is_exceeded(&self) -> bool {
        self.start_time.elapsed().as_millis() as u64 > self.max_duration_ms
    }

    pub fn remaining_ms(&self) -> u64 {
        let elapsed = self.start_time.elapsed().as_millis() as u64;
        self.max_duration_ms.saturating_sub(elapsed)
    }

    pub fn should_preempt(&self) -> bool {
        self.should_preempt.load(Ordering::Acquire)
    }

    pub fn request_preemption(&self) {
        self.should_preempt.store(true, Ordering::Release);
    }
}

pub struct CognitiveScheduler {
    budget: CognitiveBudget,
    preemption_flag: Arc<AtomicBool>,
    total_executions: Arc<AtomicU64>,
    total_timeouts: Arc<AtomicU64>,
    total_budget_exceeded: Arc<AtomicU64>,
}

impl CognitiveScheduler {
    pub fn new(budget: CognitiveBudget) -> Self {
        Self {
            budget,
            preemption_flag: Arc::new(AtomicBool::new(false)),
            total_executions: Arc::new(AtomicU64::new(0)),
            total_timeouts: Arc::new(AtomicU64::new(0)),
            total_budget_exceeded: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn request_execution(&self) -> CognitiveResult<ExecutionPermit> {
        if self.preemption_flag.load(Ordering::Acquire) {
            return Err(CognitiveError::SchedulerTimeout);
        }

        self.total_executions.fetch_add(1, Ordering::Relaxed);

        Ok(ExecutionPermit {
            start_time: Instant::now(),
            max_duration_ms: self.budget.max_execution_time_ms,
            should_preempt: Arc::clone(&self.preemption_flag),
        })
    }

    pub fn enforce_execution_limits(&self, permit: &ExecutionPermit) -> CognitiveResult<()> {
        if permit.is_exceeded() {
            self.total_timeouts.fetch_add(1, Ordering::Relaxed);
            return Err(CognitiveError::SchedulerTimeout);
        }

        if self.preemption_flag.load(Ordering::Acquire) {
            self.total_timeouts.fetch_add(1, Ordering::Relaxed);
            return Err(CognitiveError::SchedulerTimeout);
        }

        Ok(())
    }

    pub fn validate_memory_access(
        &self,
        requested_bytes: u64,
    ) -> CognitiveResult<SchedulerDecision> {
        if requested_bytes > self.budget.max_memory_bytes {
            self.total_budget_exceeded.fetch_add(1, Ordering::Relaxed);
            return Ok(SchedulerDecision::BudgetExceeded);
        }

        Ok(SchedulerDecision::Allow)
    }

    pub fn request_preemption(&self) {
        self.preemption_flag.store(true, Ordering::Release);
    }

    pub fn cancel_preemption(&self) {
        self.preemption_flag.store(false, Ordering::Release);
    }

    pub fn get_total_executions(&self) -> u64 {
        self.total_executions.load(Ordering::Acquire)
    }

    pub fn get_total_timeouts(&self) -> u64 {
        self.total_timeouts.load(Ordering::Acquire)
    }

    pub fn get_total_budget_exceeded(&self) -> u64 {
        self.total_budget_exceeded.load(Ordering::Acquire)
    }
}

impl Clone for CognitiveScheduler {
    fn clone(&self) -> Self {
        Self {
            budget: self.budget.clone(),
            preemption_flag: Arc::clone(&self.preemption_flag),
            total_executions: Arc::clone(&self.total_executions),
            total_timeouts: Arc::clone(&self.total_timeouts),
            total_budget_exceeded: Arc::clone(&self.total_budget_exceeded),
        }
    }
}

impl Default for CognitiveScheduler {
    fn default() -> Self {
        Self::new(CognitiveBudget::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_execution_permit_creation() {
        let permit = ExecutionPermit {
            start_time: Instant::now(),
            max_duration_ms: 100,
            should_preempt: Arc::new(AtomicBool::new(false)),
        };

        assert!(!permit.is_exceeded());
        assert!(permit.remaining_ms() > 0);
    }

    #[test]
    fn test_scheduler_request_execution() {
        let scheduler = CognitiveScheduler::new(CognitiveBudget::default());
        let permit = scheduler.request_execution().unwrap();

        assert!(!permit.is_exceeded());
        assert_eq!(scheduler.get_total_executions(), 1);
    }

    #[test]
    fn test_scheduler_preemption() {
        let scheduler = CognitiveScheduler::new(CognitiveBudget::default());

        scheduler.request_preemption();

        let result = scheduler.request_execution();
        assert!(result.is_err());
    }

    #[test]
    fn test_memory_budget_validation() {
        let budget = CognitiveBudget {
            max_execution_time_ms: 1000,
            max_memory_bytes: 100,
            max_reasoning_depth: 10,
        };

        let scheduler = CognitiveScheduler::new(budget);

        let small = scheduler.validate_memory_access(50).unwrap();
        assert_eq!(small, SchedulerDecision::Allow);

        let large = scheduler.validate_memory_access(200).unwrap();
        assert_eq!(large, SchedulerDecision::BudgetExceeded);
    }

    #[test]
    fn test_cancel_preemption() {
        let scheduler = CognitiveScheduler::new(CognitiveBudget::default());

        scheduler.request_preemption();
        scheduler.cancel_preemption();

        let permit = scheduler.request_execution();
        assert!(permit.is_ok());
    }
}
