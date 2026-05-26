import inspect
import re
from typing import Callable, Any, Dict, get_type_hints

# Global dictionary registry of all decorated tools
TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}

def tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that registers a Python function as a tool for the AI Agent.
    It automatically inspects the function signature, type hints, and docstrings
    to compile a comprehensive JSON Schema description of the tool.
    """
    name = func.__name__
    doc = func.__doc__ or ""
    
    # Extract the main tool description from the first part of the docstring
    doc_lines = [line.strip() for line in doc.strip().split("\n")]
    main_description = ""
    arg_descriptions: Dict[str, str] = {}
    
    in_args_section = False
    for line in doc_lines:
        if not line:
            continue
        # Detect start of argument description section (e.g., Args: or Parameters:)
        if line.lower() in ("args:", "parameters:", "arguments:"):
            in_args_section = True
            continue
        
        if in_args_section:
            # Parse argument format, e.g., "arg_name: description of the argument."
            match = re.match(r"^([\w_]+)\s*:\s*(.*)$", line)
            if match:
                arg_name = match.group(1).strip()
                arg_desc = match.group(2).strip()
                arg_descriptions[arg_name] = arg_desc
        else:
            if not main_description:
                main_description = line
            else:
                main_description += " " + line

    # Inspect function signature & type hints
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    properties: Dict[str, Dict[str, Any]] = {}
    required = []
    
    # Map Python types to JSON Schema equivalents
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

    for param_name, param in sig.parameters.items():
        # Skip self/cls parameters if they exist (though usually plain functions are tools)
        if param_name in ("self", "cls"):
            continue
            
        param_type = type_hints.get(param_name, str)
        json_type = type_mapping.get(param_type, "string")
        
        param_schema: Dict[str, Any] = {
            "type": json_type
        }
        
        # Add parameter description if found in docstrings
        if param_name in arg_descriptions:
            param_schema["description"] = arg_descriptions[param_name]
            
        # Add default values as guidance
        if param.default is not inspect.Parameter.empty:
            param_schema["default"] = param.default
        else:
            required.append(param_name)
            
        properties[param_name] = param_schema

    # Construct the JSON Tool Schema representation
    schema = {
        "name": name,
        "description": main_description.strip(),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }
    
    # Attach the custom metadata schema onto the function object
    func.tool_schema = schema  # type: ignore
    func.is_agent_tool = True  # type: ignore
    
    # Auto-register in global registry
    TOOL_REGISTRY[name] = func
    
    return func
