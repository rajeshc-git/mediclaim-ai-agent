# 🛠️ Developer Guide: Writing Custom Tools

Adding custom capabilities to this AI Agent is extremely straightforward. The agent features an automatic introspection tool engine that parses standard Python functions and converts them into schema definitions.

---

## The `@tool` Decorator

The orchestrator registers tools by importing functions wrapped in the `@tool` decorator located in `agent/tools/base.py`.

### Step 1: Define Your Function
Write a standard Python function. You **must** include:
1. **Type Annotations**: Every argument must have a defined type hint (e.g., `str`, `int`, `float`, `bool`).
2. **Docstring Guide**: Describe the function's objective, and detail each argument. This description is passed verbatim to the LLM.

### Example: A Weather Retrieval Tool

Let's build a custom weather tool:

```python
# agent/tools/weather.py
from agent.tools.base import tool

@tool
def get_weather_forecast(city: str, days: int = 1) -> str:
    """
    Fetches the weather forecast for a given city and duration.
    
    Args:
        city: The name of the city (e.g., "Paris", "New York").
        days: Number of days to forecast (1 to 7). Defaults to 1.
    """
    # Real logic or external API requests go here
    # For now, let's return a simple mock response
    return f"The forecast for {city} over the next {days} day(s) is Sunny, 22°C with light wind."
```

---

## Schema Generation Mechanics

Under the hood, the `@tool` decorator inspects the function and builds a JSON schema matching standard OpenAPI / Function calling declarations:

* **Name**: `get_weather_forecast`
* **Description**: `"Fetches the weather forecast for a given city and duration."`
* **Properties**:
  * `city`: `{ "type": "string", "description": "The name of the city (e.g., \"Paris\", \"New York\")." }`
  * `days`: `{ "type": "integer", "description": "Number of days to forecast (1 to 7). Defaults to 1." }`
* **Required Parameters**: `['city']`

---

## Registering Your Tool

To make the tool visible to the agent orchestrator, open `agent/tools/__init__.py` and expose your function inside the global `ALL_TOOLS` mapping:

```python
# agent/tools/__init__.py
from agent.tools.file_ops import read_file, write_file
from agent.tools.web_search import web_search
from agent.tools.weather import get_weather_forecast  # 1. Import your tool

# 2. Add it to the active dictionary registry
ALL_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "web_search": web_search,
    "get_weather_forecast": get_weather_forecast,
}
```

That's it! When you launch `python run.py`, the system prompt will auto-generate the weather forecasting schema, and the agent will call it whenever the user asks about the weather.

---

## Best Practices & Safety

1. **Defensive Coding**: Validate parameters inside the function. If an argument is outside bounds (e.g. `days > 7`), return a descriptive error message string. The agent will read this message and adjust its inputs.
2. **Error Isolation**: Use try-except blocks to catch exceptions. Returning an error message like `"Error: Database connection timed out. Please try again."` allows the agent to formulate an alternative plan rather than crashing the whole terminal.
3. **No Interactive Prompts**: Tools must execute to completion without blocking. Avoid using `input()` inside a tool, as the agent process runs unattended.
