import logging
import json
from typing import List, Dict, Any
from agent.config import Config

logger = logging.getLogger("agent.llm")

class GeminiClient:
    """
    Client wrapper for interacting with LLM APIs (Gemini or OpenAI).
    Features a robust mock fallback for sandbox testing when API keys are not supplied.
    """
    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.mock_mode = False
        
        if self.provider == "openai":
            self.api_key = Config.OPENAI_API_KEY
            self.model = Config.OPENAI_MODEL
            self.client = None
            
            if not self.api_key:
                logger.warning("OPENAI_API_KEY not found. Operating in MOCK mode.")
                self.mock_mode = True
                return
                
            try:
                # pyrefly: ignore [missing-import]
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI client initialized successfully with model: {self.model}")
            except ImportError:
                logger.warning("The 'openai' SDK is not installed. Defaulting to MOCK mode. Run: pip install openai")
                self.mock_mode = True
        elif self.provider == "ollama":
            self.host = Config.OLLAMA_HOST
            self.model = Config.OLLAMA_MODEL
            self.num_ctx = Config.OLLAMA_NUM_CTX
            logger.info(f"Ollama client configured successfully for model: {self.model} at {self.host} with context limit: {self.num_ctx}")
        else:
            # Default to Gemini
            self.api_key = Config.GEMINI_API_KEY
            self.model = Config.AGENT_MODEL
            self.client = None
            
            if not self.api_key:
                logger.warning("GEMINI_API_KEY not found. Operating in MOCK mode.")
                self.mock_mode = True
                return
                
            try:
                # pyrefly: ignore [missing-import]
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"GeminiClient initialized successfully with model: {self.model}")
            except ImportError:
                logger.warning("The 'google-genai' SDK is not installed. Defaulting to MOCK mode. Run: pip install google-genai")
                self.mock_mode = True

    def generate(self, messages: List[Dict[str, str]], system_instruction: str) -> str:
        """
        Sends the dialogue list to the selected LLM API (or the Mock generator)
        and retrieves the next model response.
        """
        if self.mock_mode:
            return self._generate_mock_response(messages)
            
        elif self.provider == "ollama":
            try:
                import urllib.request
                import json
                
                # Format conversational messages for Ollama API
                ollama_messages = [{"role": "system", "content": system_instruction}]
                for msg in messages:
                    if msg["role"] == "system":
                        continue
                    ollama_role = "assistant" if msg["role"] == "model" else msg["role"]
                    ollama_messages.append({"role": ollama_role, "content": msg["content"]})
                    
                payload = {
                    "model": self.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": self.num_ctx
                    }
                }
                
                url = f"{self.host.rstrip('/')}/api/chat"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if "message" in res_data and "content" in res_data["message"]:
                        return res_data["message"]["content"].strip()
                    else:
                        return "Error: Unexpected response format from local Ollama model."
            except Exception as e:
                logger.error(f"Ollama local API invocation failed: {str(e)}")
                return (
                    f"Error: Local Ollama API call failed: {str(e)}.\n"
                    f"Please make sure your local Ollama server is running (host: {self.host}) and that you "
                    f"have pulled the model using 'ollama pull {self.model}'."
                )
        elif self.provider == "openai":
            try:
                # Format conversational messages for OpenAI
                openai_messages = [{"role": "system", "content": system_instruction}]
                for msg in messages:
                    if msg["role"] == "system":
                        continue
                    # Map standard roles to OpenAI chat roles ('user', 'assistant', 'system')
                    openai_role = "assistant" if msg["role"] == "model" else msg["role"]
                    openai_messages.append({"role": openai_role, "content": msg["content"]})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    temperature=0.0
                )
                
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
                else:
                    return "Error: Empty response returned from OpenAI model."
            except Exception as e:
                logger.error(f"OpenAI API invocation failed: {str(e)}")
                return f"Error: OpenAI API call failed: {str(e)}. Please check your sk- API key and network connection."
        else:
            # Gemini execution flow
            try:
                # pyrefly: ignore [missing-import]
                from google.genai import types
                
                contents = []
                for msg in messages:
                    role = msg["role"]
                    if role == "system":
                        continue
                        
                    gemini_role = "user" if role == "user" else "model"
                    contents.append(
                        types.Content(
                            role=gemini_role,
                            parts=[types.Part.from_text(text=msg["content"])]
                        )
                    )

                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                )
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    return "Error: Empty response returned from the LLM model."
                    
            except Exception as e:
                logger.error(f"Gemini API invocation failed: {str(e)}")
                return f"Error: Gemini API call failed: {str(e)}. Please check your AIzaSy API key and network connection."

    def _generate_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generates simulated ReAct agent outputs based on dialogue history.
        This provides a flawless testing experience without requiring internet or API keys.
        """
        user_queries = [m["content"] for m in messages if m["role"] == "user" and not m["content"].startswith("Observation")]
        latest_query = user_queries[-1].lower() if user_queries else ""
        
        observations = [m["content"] for m in messages if m["content"].startswith("Observation")]
        step = len(observations)
        
        # Standard Poem Flow
        if "poem" in latest_query:
            if step == 0:
                return (
                    "Thought: The user wants to write a short poem about coding, save it to a file named 'poem.txt', "
                    "and then read it back to confirm. First, I will call the write_file tool to save the poem.\n"
                    "Action: write_file\n"
                    "Arguments: {\n"
                    "  \"filename\": \"poem.txt\",\n"
                    "  \"content\": \"In the quiet glow of midnight screens,\\nDevelopers build their digital dreams.\\nWith loops of logic and lines of art,\\nCode is the language of the modern heart.\"\n"
                    "}"
                )
            elif step == 1:
                return (
                    "Thought: Now that I have successfully written the poem to 'poem.txt', I need to read "
                    "the file back using the read_file tool to verify its contents.\n"
                    "Action: read_file\n"
                    "Arguments: {\n"
                    "  \"filename\": \"poem.txt\"\n"
                    "}"
                )
            else:
                return (
                    "Thought: I have read back the contents of the file and verified it is successfully saved. "
                    "The task is complete.\n"
                    "Final Answer: I have successfully created the file `poem.txt` with a short poem about coding, "
                    "and verified its contents by reading it back. Here is the poem:\n\n"
                    "```text\n"
                    "In the quiet glow of midnight screens,\n"
                    "Developers build their digital dreams.\n"
                    "With loops of logic and lines of art,\n"
                    "Code is the language of the modern heart.\n"
                    "```"
                )

        # Standard Search Flow
        if "search" in latest_query or "find" in latest_query or "news" in latest_query:
            if step == 0:
                return (
                    "Thought: The user is requesting external information. I should query the web_search tool "
                    "to gather facts about this topic.\n"
                    "Action: web_search\n"
                    "Arguments: {\n"
                    "  \"query\": \"" + (messages[-1]["content"] if messages else "modern AI agents") + "\"\n"
                    "}"
                )
            else:
                last_obs = observations[-1]
                return (
                    "Thought: I have retrieved the search results. I can now formulate the final answer for the user.\n"
                    "Final Answer: Based on recent search indexes, here is what I found:\n\n" + last_obs.replace("Observation:", "")
                )

        # Simple Greeting or unsupported request
        return (
            "Thought: The user request doesn't require complex tool actions. I can answer directly.\n"
            "Final Answer: Hello! I am a modern AI agent built on a modular ReAct framework. "
            "I have tools for file system manipulation (`read_file`, `write_file`, `list_directory`) "
            "and web searching (`web_search`). Let me know how I can help you today!"
        )
