import os
import logging
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load .env file from workspace root, override existing system variables
load_dotenv(override=True)

# Setup Logging Config
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent.config")

class Config:
    """
    Standard configurations for the AI Agent.
    """
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "").lower().strip()
    
    # Gemini configurations
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "").strip()
    
    # OpenAI configurations
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "").strip()
    
    # Ollama configurations
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "").strip()
    _num_ctx_str = os.getenv("OLLAMA_NUM_CTX", "").strip()
    OLLAMA_NUM_CTX: int = int(_num_ctx_str) if _num_ctx_str.isdigit() else 32768
    
    LOG_LEVEL: str = log_level_str

    @classmethod
    def validate(cls) -> bool:
        """
        Validates critical configuration presence based on the selected LLM provider.
        Returns True if successful, False if important values are missing.
        """
        if cls.LLM_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                logger.warning(
                    "LLM_PROVIDER is set to 'openai' but OPENAI_API_KEY is not defined. "
                    "The agent will operate in MOCK sandbox mode."
                )
                return False
        elif cls.LLM_PROVIDER == "ollama":
            # Ollama does not require an API key by default
            logger.info(f"Ollama local provider active, using model: {cls.OLLAMA_MODEL} at host: {cls.OLLAMA_HOST}")
            return True
        else:
            if not cls.GEMINI_API_KEY:
                logger.warning(
                    "LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not defined. "
                    "The agent will operate in MOCK sandbox mode."
                )
                return False
        return True

# Initialize a default validation scan on run
Config.validate()
