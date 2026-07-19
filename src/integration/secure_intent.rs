use std::collections::HashMap;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub type SecurityResult<T> = Result<T, SecurityError>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SecurityError {
    UntrustedSource(String),
    InvalidCapability(String),
    ResourceLimitExceeded(String),
    PathTraversalAttempt,
    PromptInjectionDetected,
    MissingRequiredCapability(String),
    IntentSchemaViolation(String),
    CapabilityViolationAttempt(String),
}

impl std::fmt::Display for SecurityError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        use SecurityError::*;
        let msg = match self {
            UntrustedSource(s) => format!("untrusted source: {}", s),
            InvalidCapability(c) => format!("invalid capability: {}", c),
            ResourceLimitExceeded(r) => format!("resource limit exceeded: {}", r),
            PathTraversalAttempt => "path traversal blocked".to_string(),
            PromptInjectionDetected => "prompt injection detected".to_string(),
            MissingRequiredCapability(c) => format!("missing capability: {}", c),
            IntentSchemaViolation(v) => format!("schema violation: {}", v),
            CapabilityViolationAttempt(m) => format!("capability violation: {}", m),
        };
        write!(f, "{}", msg)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Capability {
    FileRead,
    FileWrite,
    NetworkAccess,
    ProcessExecution,
    MemoryAccess,
    SystemCall,
    AudioAccess,
    CameraAccess,
    LocationAccess,
    ScreenAccess,
}

#[derive(Debug, Clone)]
pub struct SecureIntent {
    pub id: String,
    pub source: String,
    pub action: String,
    pub parameters: HashMap<String, String>,
    pub required_capabilities: Vec<Capability>,
    pub timestamp_ns: u64,
    pub signature: Option<String>,
}

impl SecureIntent {
    pub fn new(id: String, source: String, action: String) -> Self {
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;

        Self {
            id,
            source,
            action,
            parameters: HashMap::new(),
            required_capabilities: Vec::new(),
            timestamp_ns,
            signature: None,
        }
    }

    pub fn with_parameter(mut self, key: String, value: String) -> Self {
        self.parameters.insert(key, value);
        self
    }

    pub fn with_capability(mut self, cap: Capability) -> Self {
        if !self.required_capabilities.contains(&cap) {
            self.required_capabilities.push(cap);
        }
        self
    }

    pub fn validate_schema(&self) -> SecurityResult<()> {
        if self.id.is_empty() || self.id.len() > 256 {
            return Err(SecurityError::IntentSchemaViolation(
                "Intent ID must be 1-256 characters".to_string(),
            ));
        }

        if self.source.is_empty() || self.source.len() > 256 {
            return Err(SecurityError::IntentSchemaViolation(
                "Source must be 1-256 characters".to_string(),
            ));
        }

        if self.action.is_empty() || self.action.len() > 256 {
            return Err(SecurityError::IntentSchemaViolation(
                "Action must be 1-256 characters".to_string(),
            ));
        }

        for (key, value) in &self.parameters {
            if key.len() > 256 || value.len() > 4096 {
                return Err(SecurityError::IntentSchemaViolation(
                    "Parameter size violation".to_string(),
                ));
            }
        }

        Ok(())
    }

    pub fn validate_no_path_traversal(&self) -> SecurityResult<()> {
        let traversal_patterns = ["../", "..\\", "//", "\\\\"];

        for (key, value) in &self.parameters {
            for pattern in &traversal_patterns {
                if value.contains(pattern) {
                    return Err(SecurityError::PathTraversalAttempt);
                }
                if key.contains(pattern) {
                    return Err(SecurityError::PathTraversalAttempt);
                }
            }
        }

        Ok(())
    }

    pub fn validate_no_injection(&self) -> SecurityResult<()> {
        let injection_markers = [
            "'; DROP TABLE",
            "'; DELETE FROM",
            "UNION SELECT",
            "<script>",
            "javascript:",
            "${",
            "{{",
        ];

        for (key, value) in &self.parameters {
            let val_upper = value.to_uppercase();
            let key_upper = key.to_uppercase();
            for marker in &injection_markers {
                let marker_upper = marker.to_uppercase();
                if val_upper.contains(&marker_upper) || key_upper.contains(&marker_upper) {
                    return Err(SecurityError::PromptInjectionDetected);
                }
            }
        }

        Ok(())
    }

    pub fn validate_all(&self) -> SecurityResult<()> {
        self.validate_schema()?;
        self.validate_no_path_traversal()?;
        self.validate_no_injection()?;
        Ok(())
    }

    pub fn requires_capability(&self, cap: Capability) -> bool {
        self.required_capabilities.contains(&cap)
    }

    pub fn get_parameter(&self, key: &str) -> Option<&String> {
        self.parameters.get(key)
    }
}

pub struct CapabilityMatrix {
    permissions: Arc<HashMap<String, Vec<Capability>>>,
}

impl CapabilityMatrix {
    pub fn new() -> Self {
        Self {
            permissions: Arc::new(HashMap::new()),
        }
    }

    pub fn grant_capability(
        &mut self,
        source: String,
        capability: Capability,
    ) -> SecurityResult<()> {
        if source.len() > 256 {
            return Err(SecurityError::UntrustedSource(
                "Source name too long".to_string(),
            ));
        }
        // Use make_mut so clone-on-write handles shared Arcs correctly.
        let perms = Arc::make_mut(&mut self.permissions);
        let caps = perms.entry(source).or_default();
        if !caps.contains(&capability) {
            caps.push(capability);
        }
        Ok(())
    }

    pub fn can_execute(&self, source: &str, intent: &SecureIntent) -> SecurityResult<()> {
        for cap in &intent.required_capabilities {
            let source_caps = self
                .permissions
                .get(source)
                .ok_or_else(|| SecurityError::UntrustedSource(source.to_string()))?;

            if !source_caps.contains(cap) {
                return Err(SecurityError::CapabilityViolationAttempt(format!(
                    "Source {} lacks {:?}",
                    source, cap
                )));
            }
        }

        Ok(())
    }

    pub fn validate_intent(&self, source: &str, intent: &SecureIntent) -> SecurityResult<()> {
        intent.validate_all()?;
        self.can_execute(source, intent)?;
        Ok(())
    }
}

impl Clone for CapabilityMatrix {
    fn clone(&self) -> Self {
        Self {
            permissions: Arc::clone(&self.permissions),
        }
    }
}

impl Default for CapabilityMatrix {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_secure_intent_creation() {
        let intent = SecureIntent::new(
            "test-001".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        assert_eq!(intent.id, "test-001");
        assert_eq!(intent.source, "HumanVoice");
        assert_eq!(intent.action, "search");
        assert!(intent.parameters.is_empty());
    }

    #[test]
    fn test_schema_validation() {
        let intent = SecureIntent::new(
            "test".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );

        assert!(intent.validate_schema().is_ok());

        let invalid_id = SecureIntent::new(
            "".to_string(),
            "HumanVoice".to_string(),
            "search".to_string(),
        );
        assert!(invalid_id.validate_schema().is_err());
    }

    #[test]
    fn test_path_traversal_detection() {
        let intent = SecureIntent::new(
            "test".to_string(),
            "HumanVoice".to_string(),
            "read_file".to_string(),
        )
        .with_parameter("path".to_string(), "../../etc/passwd".to_string());

        assert_eq!(
            intent.validate_no_path_traversal(),
            Err(SecurityError::PathTraversalAttempt)
        );
    }

    #[test]
    fn test_injection_detection() {
        let intent = SecureIntent::new(
            "test".to_string(),
            "HumanVoice".to_string(),
            "execute".to_string(),
        )
        .with_parameter("cmd".to_string(), "'; DROP TABLE users; --".to_string());

        assert!(matches!(
            intent.validate_no_injection(),
            Err(SecurityError::PromptInjectionDetected)
        ));
    }

    #[test]
    fn test_capability_requirement() {
        let intent = SecureIntent::new(
            "test".to_string(),
            "HumanVoice".to_string(),
            "read".to_string(),
        )
        .with_capability(Capability::FileRead);

        assert!(intent.requires_capability(Capability::FileRead));
        assert!(!intent.requires_capability(Capability::ProcessExecution));
    }
}
