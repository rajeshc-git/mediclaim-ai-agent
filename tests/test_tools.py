import unittest
import os
import sys

# Ensure agent module is discoverable by test path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.tools.base import tool, TOOL_REGISTRY
from agent.tools.file_ops import read_file, write_file, list_directory
from agent.tools.web_search import web_search
from agent.tools.policy_extractor import get_policy_profile

class TestToolSuite(unittest.TestCase):
    """
    Tests tool decorators, schema builders, and standard file tools.
    """
    def setUp(self):
        self.test_filename = "sandbox_test_file.txt"
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def test_tool_decorator_schema_generation(self):
        @tool
        def dummy_calculation(val_a: int, val_b: float) -> str:
            """
            Computes a dummy mathematical expression.
            
            Args:
                val_a: The base integer value.
                val_b: The floating scale factor.
            """
            return str(val_a * val_b)

        self.assertIn("dummy_calculation", TOOL_REGISTRY)
        schema = getattr(dummy_calculation, "tool_schema", None)
        self.assertIsNotNone(schema)
        self.assertEqual(schema["name"], "dummy_calculation")
        self.assertEqual(schema["description"], "Computes a dummy mathematical expression.")
        self.assertEqual(schema["parameters"]["properties"]["val_a"]["type"], "integer")
        self.assertEqual(schema["parameters"]["properties"]["val_b"]["type"], "number")
        self.assertIn("val_a", schema["parameters"]["required"])

    def test_file_write_and_read_tools(self):
        # Test writing
        write_res = write_file(self.test_filename, "Unittest contents")
        self.assertIn("Success", write_res)
        self.assertTrue(os.path.exists(self.test_filename))

        # Test reading
        read_res = read_file(self.test_filename)
        self.assertEqual(read_res, "Unittest contents")

        # Test listing directory
        list_res = list_directory(".")
        self.assertIn(self.test_filename, list_res)

    def test_file_read_nonexistent(self):
        res = read_file("this_file_definitely_does_not_exist.bin")
        self.assertIn("Error", res)

    def test_web_search_tool(self):
        res = web_search("Artificial Intelligence in 2026")
        self.assertIn("Search Results", res)
        self.assertIn("Agentic workflows", res)

    def test_policy_profile_tool(self):
        # Test nonexistent query
        res_non = get_policy_profile("nonexistent_insurer_xyz")
        self.assertIn("No matching policy", res_non)
        
        # Test space-to-underscore smart matching of cached JSON profiles
        res_aditya = get_policy_profile("Aditya Birla")
        self.assertIn("Policy Rules Profile (Structured", res_aditya)
        
        res_niva = get_policy_profile("Niva Bupa")
        self.assertIn("Policy Rules Profile (Structured", res_niva)

if __name__ == "__main__":
    unittest.main()
