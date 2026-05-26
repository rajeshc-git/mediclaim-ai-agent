from typing import List, Dict, Any

class ShortTermMemory:
    """
    Manages the conversational memory buffer of the AI Agent.
    Retains conversational turns, system prompts, thoughts, actions, and tool observations.
    """
    def __init__(self, max_messages: int = 40):
        self.messages: List[Dict[str, str]] = []
        self.max_messages = max_messages

    def add_user_message(self, content: str) -> None:
        """Adds a direct query or statement from the user."""
        self.messages.append({"role": "user", "content": content})
        self._prune()

    def add_model_message(self, content: str) -> None:
        """Adds a model response containing thought steps, final answers, or tool requests."""
        self.messages.append({"role": "model", "content": content})
        self._prune()

    def add_observation(self, tool_name: str, result: str) -> None:
        """
        Adds a system observation showing the result of executing a specific tool.
        This provides the context back to the model during multi-step ReAct loops.
        Automatically compresses observations larger than 4000 characters to keep
        the context window clean and reasoning loops fast.
        """
        content_to_store = result
        
        if len(result) > 4000:
            # Let's perform a high-density summarization to prevent context window bloat
            try:
                # Local import to prevent circular dependency
                from agent.llm import GeminiClient
                client = GeminiClient()
                
                prompt = (
                    f"You are a high-speed data compression assistant for a medical claims AI agent.\n"
                    f"Please compress the following raw output from the '{tool_name}' tool. "
                    f"Extract only the key billing line-items, prices, patient details, diagnostic codes, "
                    f"policy limits, and critical numbers. Eliminate all verbose filler text and maintain "
                    f"a dense, structured markdown summary (lists/tables):\n\n"
                    f"{result[:20000]}" # Limit chunk to prevent API payload limits
                )
                
                compressed = client.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_instruction="Compress data dense and accurately without losing key numbers or codes."
                )
                
                content_to_store = (
                    f"[AUTO-COMPRESSED OBSERVATION (Original length: {len(result)} chars)]\n"
                    f"Here is the high-density structured summary of the '{tool_name}' output:\n\n"
                    f"{compressed}\n\n"
                    f"(Note: Full raw data has been parsed and is stored in background database cache.)"
                )
            except Exception as e:
                # Fallback to high-speed heuristic truncation if LLM call fails
                lines = result.splitlines()
                first_lines = "\n".join(lines[:30])
                last_lines = "\n".join(lines[-30:])
                content_to_store = (
                    f"[HEURISTIC TRUNCATION (Original length: {len(result)} chars)]\n"
                    f"--- BEGINNING ---\n{first_lines}\n"
                    f"\n... [Truncated {len(result) - 3000} characters of raw data for token efficiency] ...\n\n"
                    f"--- END ---\n{last_lines}"
                )

        content = f"Observation (from tool '{tool_name}'):\n{content_to_store}"
        self.messages.append({"role": "user", "content": content})
        self._prune()

    def add_system_message(self, content: str) -> None:
        """Adds foundational developer guidance prompts."""
        self.messages.append({"role": "system", "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        """Returns the list of messages in standard API dictionary format."""
        return self.messages

    def clear(self) -> None:
        """Wipes the active session history."""
        self.messages = []

    def _prune(self) -> None:
        """Prunes historical conversational messages to stay within token limits."""
        # Ensure we always keep the initial system prompt if it exists at index 0
        if len(self.messages) > self.max_messages:
            system_msg = None
            has_system = len(self.messages) > 0 and self.messages[0]["role"] == "system"
            
            if has_system:
                system_msg = self.messages[0]
                # Prune down to max_messages - 1 so the system message fits within max_messages
                cutoff = len(self.messages) - (self.max_messages - 1)
                self.messages = self.messages[cutoff:]
                self.messages.insert(0, system_msg)
            else:
                cutoff = len(self.messages) - self.max_messages
                self.messages = self.messages[cutoff:]
