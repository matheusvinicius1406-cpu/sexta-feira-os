"""
Jarvis AI System - Integration of OpenJarvis concepts with Sexta-Feira OS
Lightweight, Gemini-focused personal AI assistant
"""

import json
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Agent capabilities"""
    CHAT = "chat"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    LEARNING = "learning"
    SCHEDULING = "scheduling"


@dataclass
class Tool:
    """Tool definition for agents"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    function: Optional[callable] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "enabled": self.enabled,
        }


@dataclass
class Agent:
    """Intelligent Agent with capabilities and tools"""
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)
    personality: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    
    def add_tool(self, tool: Tool) -> None:
        """Add a tool to the agent"""
        self.tools.append(tool)
        logger.info(f"Tool '{tool.name}' added to agent '{self.name}'")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has capability"""
        return capability in self.capabilities
    
    def get_system_prompt(self) -> str:
        """Get full system prompt for this agent"""
        if self.system_prompt:
            return self.system_prompt
        
        prompt = f"You are {self.name}, a personal AI assistant.\n"
        prompt += f"Description: {self.description}\n"
        if self.personality:
            prompt += f"Personality: {self.personality}\n"
        
        if self.tools:
            prompt += "\nAvailable tools:\n"
            for tool in self.tools:
                if tool.enabled:
                    prompt += f"- {tool.name}: {tool.description}\n"
        
        return prompt


@dataclass
class JarvisMemory:
    """Lightweight memory system inspired by OpenJarvis"""
    entries: Dict[str, Any] = field(default_factory=dict)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    max_interactions: int = 100
    
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """Store in memory"""
        self.entries[key] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        logger.debug(f"Stored memory entry: {key}")
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve from memory"""
        if key in self.entries:
            return self.entries[key]["value"]
        return None
    
    def add_interaction(self, user_input: str, ai_response: str, context: Dict = None) -> None:
        """Track interaction for learning"""
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "context": context or {}
        }
        self.interactions.append(interaction)
        
        # Keep only recent interactions
        if len(self.interactions) > self.max_interactions:
            self.interactions.pop(0)
    
    def get_recent_context(self, limit: int = 5) -> str:
        """Get recent interaction context"""
        if not self.interactions:
            return ""
        
        recent = self.interactions[-limit:]
        context = "Recent interactions:\n"
        for interaction in recent:
            context += f"User: {interaction['user_input']}\n"
            context += f"Assistant: {interaction['ai_response']}\n\n"
        
        return context


@dataclass
class JarvisConfig:
    """Configuration for Jarvis system"""
    gemini_api_key: str
    default_model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    max_tokens: int = 2000
    system_name: str = "Jarvis"
    enable_memory: bool = True
    enable_learning: bool = True
    enable_tools: bool = True


class ToolRegistry:
    """Registry for tools"""
    _tools: Dict[str, Tool] = {}
    
    @classmethod
    def register(cls, tool: Tool) -> None:
        """Register a tool"""
        cls._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Tool]:
        """Get a tool"""
        return cls._tools.get(name)
    
    @classmethod
    def list_all(cls) -> List[Tool]:
        """List all tools"""
        return list(cls._tools.values())
    
    @classmethod
    def list_enabled(cls) -> List[Tool]:
        """List enabled tools"""
        return [tool for tool in cls._tools.values() if tool.enabled]


class AgentRegistry:
    """Registry for agents"""
    _agents: Dict[str, Agent] = {}
    
    @classmethod
    def register(cls, agent: Agent) -> None:
        """Register an agent"""
        cls._agents[agent.id] = agent
        logger.info(f"Agent registered: {agent.name} ({agent.id})")
    
    @classmethod
    def get(cls, agent_id: str) -> Optional[Agent]:
        """Get an agent"""
        return cls._agents.get(agent_id)
    
    @classmethod
    def list_all(cls) -> List[Agent]:
        """List all agents"""
        return list(cls._agents.values())
    
    @classmethod
    def get_by_capability(cls, capability: AgentCapability) -> List[Agent]:
        """Get agents with specific capability"""
        return [a for a in cls._agents.values() if a.has_capability(capability)]


class JarvisSystem:
    """Main Jarvis AI System"""
    
    def __init__(self, config: JarvisConfig):
        self.config = config
        self.memory = JarvisMemory() if config.enable_memory else None
        self.agents: Dict[str, Agent] = {}
        logger.info(f"Jarvis system initialized: {config.system_name}")
    
    def create_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: List[AgentCapability] = None,
        personality: str = "",
    ) -> Agent:
        """Create a new agent"""
        agent = Agent(
            id=agent_id,
            name=name,
            description=description,
            capabilities=capabilities or [AgentCapability.CHAT],
            personality=personality,
        )
        self.agents[agent_id] = agent
        AgentRegistry.register(agent)
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def add_tool_to_agent(self, agent_id: str, tool: Tool) -> bool:
        """Add tool to agent"""
        agent = self.get_agent(agent_id)
        if agent:
            agent.add_tool(tool)
            ToolRegistry.register(tool)
            return True
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "system_name": self.config.system_name,
            "agents_count": len(self.agents),
            "tools_count": len(ToolRegistry.list_all()),
            "memory_enabled": self.config.enable_memory,
            "memory_entries": len(self.memory.entries) if self.memory else 0,
            "interactions_tracked": len(self.memory.interactions) if self.memory else 0,
        }
