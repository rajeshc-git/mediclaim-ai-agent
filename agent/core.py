import os
import re
import json
import logging
from typing import Dict, Any, Callable, List, Generator
from agent.config import Config
from agent.llm import GeminiClient
from agent.memory import ShortTermMemory
from agent.tools import ALL_TOOLS

logger = logging.getLogger("agent.core")

class AgentOrchestrator:
    """
    The main coordinator for the AI Agent.
    Manages prompt parsing, execution loops, tool calling, and short-term memory.
    """
    def __init__(self, max_iterations: int = 25):
        self.llm = GeminiClient()
        self.memory = ShortTermMemory()
        self.max_iterations = max_iterations
        self.system_prompt_template = self._load_system_prompt()
        self._prewarm_policy_cache()

    def _prewarm_policy_cache(self) -> None:
        """Finds all policy guidelines PDFs and Excel sheets and triggers structured extraction to warm up cache."""
        try:
            from agent.tools.policy_extractor import extract_policy_profile, extract_policy_profile_from_excel
            rules_dir = os.path.normpath("insurance_rules")
            if os.path.exists(rules_dir) and os.path.isdir(rules_dir):
                for file in os.listdir(rules_dir):
                    if file.lower().endswith(".pdf"):
                        pdf_path = os.path.join(rules_dir, file)
                        extract_policy_profile(pdf_path)
                    elif file.lower().endswith(".xlsx"):
                        xlsx_path = os.path.join(rules_dir, file)
                        extract_policy_profile_from_excel(xlsx_path)
        except Exception as e:
            logger.warning(f"Failed to pre-warm policy cache: {str(e)}")

    def _load_system_prompt(self) -> str:
        """Loads the raw system prompt markdown file."""
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "system.md"
        )
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"System prompt template not found at: {prompt_path}")
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_tools_schema_string(self) -> str:
        """
        Iterates over all registered functions in the tool dictionary,
        retrieves their auto-generated schemas, and formats them into a readable list.
        """
        schemas = []
        for name, func in ALL_TOOLS.items():
            schema = getattr(func, "tool_schema", None)
            if schema:
                schemas.append(json.dumps(schema, indent=2))
        return "\n\n".join(schemas)

    @staticmethod
    def _extract_json_block(text: str, keyword: str = "Arguments:") -> str:
        """
        Extracts a JSON object block following a keyword by counting balanced
        braces. This correctly handles nested objects, arrays, and braces
        embedded inside JSON string values (escaped with backslash).
        Returns the extracted JSON string, or None if not found.
        """
        # Case-insensitive keyword search
        keyword_lower = keyword.lower()
        text_lower = text.lower()
        idx = text_lower.find(keyword_lower)
        if idx == -1:
            return None
            
        # Find the first opening brace after the keyword
        start = text.find("{", idx + len(keyword))
        if start == -1:
            return None
            
        depth = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            ch = text[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if ch == '\\':
                escape_next = True
                continue
                
            if ch == '"':
                in_string = not in_string
                continue
                
            if in_string:
                continue
                
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
                    
        # Unbalanced braces — return best effort up to end
        return None

    def run(self, user_input: str) -> Generator[Dict[str, Any], None, str]:
        """
        Runs the ReAct loop for a given user query.
        Yields logs at each step so they can be rendered in real-time in the terminal.
        Returns the final response string.
        """
        self.memory.add_user_message(user_input)
        
        # Prepare the system prompt by injecting tool schemas
        tool_schemas_str = self._get_tools_schema_string()
        system_instruction = self.system_prompt_template.replace(
            "${TOOL_SCHEMAS}", tool_schemas_str
        )

        consecutive_fallbacks = 0  # Track consecutive parse failures

        for iteration in range(self.max_iterations):
            yield {"type": "step_start", "step": iteration + 1}

            # Fetch LLM decision
            messages = self.memory.get_messages()
            response_text = self.llm.generate(messages, system_instruction)
            
            yield {"type": "llm_raw", "text": response_text}

            # Parse ReAct components case-insensitively and flexibly
            thought_match = re.search(r"(?:Thought|THOUGHT)\s*:\s*(.*?)(?=(?:Action|ACTION|Final\s+Answer|FINAL\s+ANSWER|$))", response_text, re.DOTALL | re.IGNORECASE)
            action_match = re.search(r"(?:Action|ACTION)\s*:\s*([\w_]+)", response_text, re.IGNORECASE)
            final_match = re.search(r"(?:Final\s+Answer|FINAL\s+ANSWER)\s*:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)

            thought = thought_match.group(1).strip() if thought_match else ""
            if thought:
                yield {"type": "thought", "text": thought}

            # Add model's turn to memory
            self.memory.add_model_message(response_text)

            # Check if final answer is supplied
            if final_match:
                final_answer = final_match.group(1).strip()
                yield {"type": "final_answer", "text": final_answer}
                return final_answer

            # If action is requested
            if action_match:
                consecutive_fallbacks = 0  # Reset fallback counter on valid action
                tool_name = action_match.group(1).strip()
                
                # Use the robust brace-balanced JSON extractor instead of regex
                args_str = self._extract_json_block(response_text, "Arguments:")
                if not args_str:
                    args_str = "{}"
                
                try:
                    tool_args = json.loads(args_str)
                except json.JSONDecodeError:
                    observation = f"Error: Arguments must be a valid JSON object. Got: {args_str[:500]}"
                    yield {"type": "tool_error", "tool": tool_name, "error": observation}
                    self.memory.add_observation(tool_name, observation)
                    continue

                yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

                # Resolve and execute tool
                if tool_name in ALL_TOOLS:
                    try:
                        observation = ALL_TOOLS[tool_name](**tool_args)
                        # Ensure we convert standard non-string returns to strings
                        if not isinstance(observation, str):
                            observation = str(observation)
                    except Exception as e:
                        observation = f"Error: Tool execution raised an exception: {str(e)}"
                else:
                    observation = f"Error: Tool '{tool_name}' is not recognized. Available tools: {list(ALL_TOOLS.keys())}"

                yield {"type": "tool_observation", "tool": tool_name, "observation": observation}
                
                # Append tool observation to short-term memory
                self.memory.add_observation(tool_name, observation)
                
            else:
                # No Action tag and no Final Answer tag detected.
                # Instead of treating this as a final answer (which causes premature termination),
                # nudge the agent to retry with proper formatting — up to 3 consecutive failures.
                consecutive_fallbacks += 1
                
                if consecutive_fallbacks >= 3:
                    # After 3 consecutive formatting failures, treat as final answer to prevent infinite loops
                    fallback_answer = response_text.replace(f"Thought: {thought}", "").strip()
                    if not fallback_answer:
                        fallback_answer = response_text
                    yield {"type": "final_answer", "text": fallback_answer}
                    return fallback_answer
                
                # Add a corrective guidance observation to memory so the LLM retries
                guidance = (
                    "Observation (system): Your previous response was missing the required 'Action:' or 'Final Answer:' prefix. "
                    "You MUST use the exact format:\n"
                    "Action: tool_name\n"
                    "Arguments: { ... valid JSON ... }\n\n"
                    "OR if the task is complete:\n"
                    "Final Answer: your complete response\n\n"
                    "Please retry with the correct format now."
                )
                yield {"type": "thought", "text": "⚠️ [System Notification] Response was missing required 'Action:' or 'Final Answer:' prefix. Nudging the agent to retry with correct formatting..."}
                self.memory.add_observation("format_parser", guidance)

        # If loop exhausts max iterations
        timeout_msg = "Error: Agent reached maximum reasoning steps without producing a final answer."
        yield {"type": "final_answer", "text": timeout_msg}
        return timeout_msg

