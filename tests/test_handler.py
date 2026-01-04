
import unittest
import sys
import os

sys.path.append(os.getcwd())

from vectordb.core.handler import JSONHandler

class TestJSONHandler(unittest.TestCase):
    
    def test_auto_strategy(self):
        handler = JSONHandler(strategy='auto')
        doc = {
            "title": "Main Title",
            "content": "Some body content",
            "random": "ignore me"
        }
        res = handler.process(doc)
        self.assertEqual(res["_text"], "Main Title", "Auto should pick title first")
        
        doc2 = {"description": "A description"}
        res2 = handler.process(doc2)
        self.assertEqual(res2["_text"], "A description", "Auto should pick description if title missing")

    def test_flattening(self):
        handler = JSONHandler(strategy='auto')
        doc = {
            "title": "Flat",
            "meta": {
                "user": {
                    "name": "Alice",
                    "id": 1
                },
                "tags": ["a", "b"]
            }
        }
        res = handler.process(doc)
        
        self.assertEqual(res["meta_user_name"], "Alice")
        self.assertEqual(res["meta_user_id"], 1)
        self.assertEqual(res["meta_tags_0"], "a")
        self.assertEqual(res["meta_tags_1"], "b")
        
    def test_reserved_fields(self):
        handler = JSONHandler(strategy='auto')
        doc = {
            "title": "Hack",
            "_id": "admin_access",
            "_vector": [1, 2, 3]
        }
        res = handler.process(doc)
        self.assertNotIn("_id", res)
        self.assertNotIn("_vector", res)
        self.assertEqual(res["title"], "Hack")

    def test_concat_strategy(self):
        handler = JSONHandler(strategy='concat_all')
        doc = {
            "part1": "Hello",
            "nested": {"part2": "World"},
            "ignored": 123
        }
        res = handler.process(doc)
        text = res["_text"]
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertIn("123", text)

if __name__ == '__main__':
    unittest.main()
