use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub type ToolResult<T> = Result<T, ToolError>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ToolError {
    ToolNotFound(String),
    ExecutionTimeout,
    ExecutionFailed(String),
    InvalidInput(String),
    ResourceLimitExceeded(String),
    SandboxError(String),
}

impl std::fmt::Display for ToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ToolError::ToolNotFound(name) => write!(f, "Tool not found: {}", name),
            ToolError::ExecutionTimeout => write!(f, "Tool execution timeout"),
            ToolError::ExecutionFailed(msg) => write!(f, "Tool execution failed: {}", msg),
            ToolError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            ToolError::ResourceLimitExceeded(res) => write!(f, "Resource limit exceeded: {}", res),
            ToolError::SandboxError(msg) => write!(f, "Sandbox error: {}", msg),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToolInput {
    pub tool_name: String,
    pub operation: String,
    pub parameters: HashMap<String, String>,
    pub timeout_ms: u64,
}

impl ToolInput {
    pub fn new(tool_name: String, operation: String) -> Self {
        Self {
            tool_name,
            operation,
            parameters: HashMap::new(),
            timeout_ms: 5000,
        }
    }

    pub fn with_parameter(mut self, key: String, value: String) -> Self {
        self.parameters.insert(key, value);
        self
    }

    pub fn with_timeout_ms(mut self, ms: u64) -> Self {
        self.timeout_ms = ms;
        self
    }

    pub fn validate(&self) -> ToolResult<()> {
        if self.tool_name.is_empty() || self.tool_name.len() > 256 {
            return Err(ToolError::InvalidInput("Tool name invalid".to_string()));
        }

        if self.operation.is_empty() || self.operation.len() > 256 {
            return Err(ToolError::InvalidInput("Operation invalid".to_string()));
        }

        for (key, value) in &self.parameters {
            if key.len() > 256 || value.len() > 8192 {
                return Err(ToolError::InvalidInput(
                    "Parameter size violation".to_string(),
                ));
            }
        }

        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct ToolOutput {
    pub tool_name: String,
    pub status: ToolOutputStatus,
    pub result: String,
    pub duration_ms: u64,
    pub timestamp_ns: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToolOutputStatus {
    Success,
    Timeout,
    Failed,
}

impl ToolOutput {
    pub fn success(tool_name: String, result: String, duration_ms: u64) -> Self {
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            tool_name,
            status: ToolOutputStatus::Success,
            result,
            duration_ms,
            timestamp_ns,
        }
    }

    pub fn failed(tool_name: String, reason: String, duration_ms: u64) -> Self {
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            tool_name,
            status: ToolOutputStatus::Failed,
            result: reason,
            duration_ms,
            timestamp_ns,
        }
    }

    pub fn timeout(tool_name: String, duration_ms: u64) -> Self {
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            tool_name,
            status: ToolOutputStatus::Timeout,
            result: "Execution timeout".to_string(),
            duration_ms,
            timestamp_ns,
        }
    }
}

pub struct ToolExecutor {
    tools: Arc<HashMap<String, Arc<dyn Fn(&ToolInput) -> ToolResult<String> + Send + Sync>>>,
    max_concurrent_executions: usize,
    active_executions: Arc<AtomicU64>,
    total_executions: Arc<AtomicU64>,
    total_timeouts: Arc<AtomicU64>,
    total_failures: Arc<AtomicU64>,
}

impl ToolExecutor {
    pub fn new(max_concurrent: usize) -> Self {
        Self {
            tools: Arc::new(HashMap::new()),
            max_concurrent_executions: max_concurrent,
            active_executions: Arc::new(AtomicU64::new(0)),
            total_executions: Arc::new(AtomicU64::new(0)),
            total_timeouts: Arc::new(AtomicU64::new(0)),
            total_failures: Arc::new(AtomicU64::new(0)),
        }
    }

    pub fn execute(&self, input: ToolInput) -> ToolResult<ToolOutput> {
        input.validate()?;

        let active = self.active_executions.load(Ordering::Acquire);
        if active >= self.max_concurrent_executions as u64 {
            return Err(ToolError::ResourceLimitExceeded(
                "Max concurrent executions".to_string(),
            ));
        }

        self.active_executions.fetch_add(1, Ordering::Relaxed);
        self.total_executions.fetch_add(1, Ordering::Relaxed);

        let start_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        let tool_name = input.tool_name.clone();
        let result = match self.tools.get(&input.tool_name) {
            Some(tool) => tool(&input),
            None => Err(ToolError::ToolNotFound(input.tool_name.clone())),
        };

        let end_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        let duration_ms = (end_ns - start_ns) / 1_000_000;

        if duration_ms > input.timeout_ms {
            self.total_timeouts.fetch_add(1, Ordering::Relaxed);
            self.active_executions.fetch_sub(1, Ordering::Relaxed);
            return Ok(ToolOutput::timeout(tool_name, duration_ms));
        }

        let output = match result {
            Ok(output_str) => ToolOutput::success(tool_name, output_str, duration_ms),
            Err(_e) => {
                self.total_failures.fetch_add(1, Ordering::Relaxed);
                ToolOutput::failed(tool_name, "Execution error".to_string(), duration_ms)
            }
        };

        self.active_executions.fetch_sub(1, Ordering::Relaxed);

        Ok(output)
    }

    pub fn metrics(&self) -> ToolExecutorMetrics {
        ToolExecutorMetrics {
            active_executions: self.active_executions.load(Ordering::Acquire),
            total_executions: self.total_executions.load(Ordering::Acquire),
            total_timeouts: self.total_timeouts.load(Ordering::Acquire),
            total_failures: self.total_failures.load(Ordering::Acquire),
        }
    }
}

pub struct ToolExecutorMetrics {
    pub active_executions: u64,
    pub total_executions: u64,
    pub total_timeouts: u64,
    pub total_failures: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tool_input_creation() {
        let input = ToolInput::new("search".to_string(), "query".to_string());
        assert_eq!(input.tool_name, "search");
        assert_eq!(input.operation, "query");
    }

    #[test]
    fn test_tool_input_validation() {
        let valid = ToolInput::new("search".to_string(), "query".to_string());
        assert!(valid.validate().is_ok());

        let invalid_tool = ToolInput::new("".to_string(), "query".to_string());
        assert!(invalid_tool.validate().is_err());
    }

    #[test]
    fn test_tool_output_success() {
        let output = ToolOutput::success("search".to_string(), "result".to_string(), 100);

        assert_eq!(output.status, ToolOutputStatus::Success);
        assert_eq!(output.duration_ms, 100);
    }

    #[test]
    fn test_tool_output_timeout() {
        let output = ToolOutput::timeout("search".to_string(), 5100);
        assert_eq!(output.status, ToolOutputStatus::Timeout);
    }

    #[test]
    fn test_tool_executor_metrics() {
        let executor = ToolExecutor::new(10);
        let metrics = executor.metrics();

        assert_eq!(metrics.active_executions, 0);
        assert_eq!(metrics.total_executions, 0);
    }
}
