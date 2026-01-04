
import unittest
import json
import sys
import os

sys.path.append(os.getcwd())

from vectordb.core.handler import JSONHandler

class TestUniversalJSON(unittest.TestCase):
    """
    Stress tests for the Universal JSON Handler.
    Goal: Prove it can handle ANY JSON structure without crashing.
    """
    
    def setUp(self):
        self.handler = JSONHandler(strategy='auto')

    def test_deeply_nested_structure(self):
        """Test nesting beyond the 5-level flattening limit."""
        print("\n--- Test 1: Deep Nesting ---")
        deep_json = {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": "too_deep"}}}}}}
        
        res = self.handler.process(deep_json)
        
        # Should be flattened up to level 5, level 6 might be ignored or kept as dict depending on logic
        # Current logic stops recursion at max_depth=5.
        # Let's check keys.
        self.assertIn("level1_level2_level3_level4_level5_level6", res, "Should flatten deep keys if possible or truncate safely")
        print(f"Deep keys flattened: {list(res.keys())}")

    def test_mixed_array_types(self):
        """Test arrays with mixed types (int, string, dict, list)."""
        print("\n--- Test 2: Mixed Arrays ---")
        mixed = {
            "mixed_list": [
                1, 
                "string", 
                {"nested_in_list": "value"}, 
                [1, 2] # List in list
            ]
        }
        res = self.handler.process(mixed)
        
        # Check if list[0] (int) is preserved
        self.assertEqual(res.get("mixed_list_0"), 1)
        # Check if list[2] (dict) is flattened
        self.assertEqual(res.get("mixed_list_2_nested_in_list"), "value")
        # Check if list[3] (list) is handled (might be skipped by current recursion or flattened)
        print(f"Mixed Array Keys: {list(res.keys())}")
        
    def test_crazy_types(self):
        """Test nulls, booleans, empty structures."""
        print("\n--- Test 3: Edge Cases ---")
        crazy = {
            "empty_dict": {},
            "empty_list": [],
            "null_value": None,
            "bool_true": True,
            "bool_false": False,
            "unicode_key_한글": "value_한글"
        }
        res = self.handler.process(crazy)
        self.assertEqual(res.get("bool_true"), True)
        self.assertEqual(res.get("unicode_key_한글"), "value_한글")
        print("Processed Crazy Types successfully")

    def test_text_extraction_priority(self):
        """Ensure _text extraction works when multiple candidates exist."""
        print("\n--- Test 4: Text Extraction ---")
        doc = {
            "meta": {"ignored": "data"},
            "body": "This is the real content",
            "title": "This is the title" 
        }
        res = self.handler.process(doc)
        # 'title' has higher priority than 'body' in 'auto' strategy
        self.assertEqual(res["_text"], "This is the title") 
        print(f"Extracted Text: {res['_text']}")

if __name__ == '__main__':
    unittest.main()
