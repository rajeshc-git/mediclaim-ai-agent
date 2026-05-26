import unittest
import os
import sys

# Ensure agent module is discoverable by test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import ShortTermMemory
from agent.core import AgentOrchestrator

class TestAgentComponents(unittest.TestCase):
    """
    Unit tests targeting agent memory buffers and orchestrator setups.
    """
    def setUp(self):
        self.memory = ShortTermMemory(max_messages=5)

    def test_memory_add_and_prune(self):
        # Adding messages
        self.memory.add_system_message("System instruction")
        self.memory.add_user_message("Hello 1")
        self.memory.add_model_message("Hi 1")
        self.memory.add_user_message("Hello 2")
        self.memory.add_model_message("Hi 2")
        
        messages = self.memory.get_messages()
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["content"], "Hi 2")
        
        # Adding one more message trigger pruning
        self.memory.add_user_message("Hello 3")
        messages = self.memory.get_messages()
        
        # Total messages capped at max_messages (5)
        self.assertEqual(len(messages), 5)
        # Ensure system prompt remains at position 0
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["content"], "Hello 3")

    def test_memory_clear(self):
        self.memory.add_user_message("test")
        self.memory.clear()
        self.assertEqual(len(self.memory.get_messages()), 0)

    def test_orchestrator_initialization(self):
        orchestrator = AgentOrchestrator()
        self.assertIsNotNone(orchestrator.system_prompt_template)
        self.assertIn("ReAct Agent Orchestration", orchestrator.system_prompt_template)

if __name__ == "__main__":
    unittest.main()
