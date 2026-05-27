use crate::cognition::cognitive_errors::{CognitiveError, CognitiveResult};
use std::collections::HashMap;
use std::sync::Arc;

#[derive(Debug, Clone)]
pub enum ToolCapability {
    FileAccess,
    NetworkAccess,
    ProcessExecution,
    MemoryAccess,
    SystemCall,
}

impl ToolCapability {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::FileAccess => "file_access",
            Self::NetworkAccess => "network_access",
            Self::ProcessExecution => "process_execution",
            Self::MemoryAccess => "memory_access",
            Self::SystemCall => "system_call",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "file_access" => Some(Self::FileAccess),
            "network_access" => Some(Self::NetworkAccess),
            "process_execution" => Some(Self::ProcessExecution),
            "memory_access" => Some(Self::MemoryAccess),
            "system_call" => Some(Self::SystemCall),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ToolSignature {
    pub name: String,
    pub version: String,
    pub hash: u64,
    pub required_capabilities: Vec<ToolCapability>,
}

impl ToolSignature {
    pub fn new(name: String, version: String) -> Self {
        Self {
            name,
            version,
            hash: 0,
            required_capabilities: Vec::new(),
        }
    }

    pub fn with_capability(mut self, cap: ToolCapability) -> Self {
        self.required_capabilities.push(cap);
        self
    }

    pub fn compute_hash(&mut self) {
        let mut hash = 0xcbf29ce484222325u64;
        const PRIME: u64 = 0x100000001b3;

        hash ^= fnv_hash_str(&self.name);
        hash = hash.wrapping_mul(PRIME);

        hash ^= fnv_hash_str(&self.version);
        hash = hash.wrapping_mul(PRIME);

        self.hash = hash;
    }
}

pub struct ToolRegistry {
    tools: Arc<HashMap<String, ToolSignature>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: Arc::new(HashMap::new()),
        }
    }

    pub fn register_tool(&mut self, mut signature: ToolSignature) -> CognitiveResult<()> {
        if signature.name.is_empty() {
            return Err(CognitiveError::RegistryError(
                "Tool name cannot be empty".to_string(),
            ));
        }

        if signature.name.len() > 256 {
            return Err(CognitiveError::RegistryError(
                "Tool name too long".to_string(),
            ));
        }

        signature.compute_hash();

        let mut new_tools = (*self.tools).clone();
        new_tools.insert(signature.name.clone(), signature);
        self.tools = Arc::new(new_tools);

        Ok(())
    }

    pub fn resolve_tool(&self, name: &str) -> CognitiveResult<ToolSignature> {
        self.tools
            .get(name)
            .cloned()
            .ok_or_else(|| CognitiveError::ToolNotFound(name.to_string()))
    }

    pub fn validate_tool_access(
        &self,
        tool_name: &str,
        required_caps: &[ToolCapability],
    ) -> CognitiveResult<()> {
        let tool = self.resolve_tool(tool_name)?;

        for required_cap in required_caps {
            let has_cap = tool
                .required_capabilities
                .iter()
                .any(|c| std::mem::discriminant(c) == std::mem::discriminant(required_cap));

            if !has_cap {
                return Err(CognitiveError::CapabilityViolation(format!(
                    "Tool {} does not have capability {}",
                    tool_name,
                    required_cap.as_str()
                )));
            }
        }

        Ok(())
    }

    pub fn tool_exists(&self, name: &str) -> bool {
        self.tools.contains_key(name)
    }

    pub fn list_tools(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    pub fn get_tool_count(&self) -> usize {
        self.tools.len()
    }
}

impl Clone for ToolRegistry {
    fn clone(&self) -> Self {
        Self {
            tools: Arc::clone(&self.tools),
        }
    }
}

impl Default for ToolRegistry {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tool_registry_creation() {
        let registry = ToolRegistry::new();
        assert_eq!(registry.get_tool_count(), 0);
    }

    #[test]
    fn test_register_tool() {
        let mut registry = ToolRegistry::new();
        let sig = ToolSignature::new("search".to_string(), "1.0".to_string())
            .with_capability(ToolCapability::FileAccess);

        let result = registry.register_tool(sig);
        assert!(result.is_ok());
        assert_eq!(registry.get_tool_count(), 1);
    }

    #[test]
    fn test_resolve_tool() {
        let mut registry = ToolRegistry::new();
        let sig = ToolSignature::new("search".to_string(), "1.0".to_string());

        registry.register_tool(sig).unwrap();

        let resolved = registry.resolve_tool("search");
        assert!(resolved.is_ok());
        assert_eq!(resolved.unwrap().name, "search");
    }

    #[test]
    fn test_tool_not_found() {
        let registry = ToolRegistry::new();
        let result = registry.resolve_tool("nonexistent");

        assert!(result.is_err());
    }

    #[test]
    fn test_validate_tool_access() {
        let mut registry = ToolRegistry::new();
        let sig = ToolSignature::new("fs".to_string(), "1.0".to_string())
            .with_capability(ToolCapability::FileAccess);

        registry.register_tool(sig).unwrap();

        let result = registry.validate_tool_access("fs", &[ToolCapability::FileAccess]);
        assert!(result.is_ok());
    }

    #[test]
    fn test_capability_violation() {
        let mut registry = ToolRegistry::new();
        let sig = ToolSignature::new("fs".to_string(), "1.0".to_string())
            .with_capability(ToolCapability::FileAccess);

        registry.register_tool(sig).unwrap();

        let result = registry.validate_tool_access("fs", &[ToolCapability::ProcessExecution]);
        assert!(result.is_err());
    }
}
