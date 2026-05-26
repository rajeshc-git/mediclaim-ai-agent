# Import tool modules to ensure decorators are executed and registered
from agent.tools import file_ops
from agent.tools import web_search
from agent.tools import medical
from agent.tools import policy_extractor

# Import the registry directly from base
from agent.tools.base import TOOL_REGISTRY

# Expose a clean, complete dict mapping of active tools
ALL_TOOLS = TOOL_REGISTRY

__all__ = ["ALL_TOOLS", "TOOL_REGISTRY"]
