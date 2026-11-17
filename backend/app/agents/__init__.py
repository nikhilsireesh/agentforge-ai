"""The six AgentForge agents, keyed by their stable names."""

from app.agents.architect import SolutionArchitectAgent
from app.agents.base import BaseAgent
from app.agents.developer import DeveloperAgent
from app.agents.documentation import DocumentationAgent
from app.agents.requirement_analyst import RequirementAnalystAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewTestingAgent

AGENTS: dict[str, BaseAgent] = {
    agent.name: agent
    for agent in (
        RequirementAnalystAgent(),
        ResearchAgent(),
        SolutionArchitectAgent(),
        DeveloperAgent(),
        ReviewTestingAgent(),
        DocumentationAgent(),
    )
}

AGENT_ORDER = list(AGENTS)

__all__ = ["AGENTS", "AGENT_ORDER", "BaseAgent"]
