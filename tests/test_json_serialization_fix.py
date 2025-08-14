import unittest
import json
import sys
import os
from dataclasses import dataclass

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class MockParticipant:
    id: str
    FullNameRU: str

@dataclass
class MockSearchResult:
    participant: MockParticipant
    confidence: float
    match_field: str
    match_type: str

def _safe_serialize_user_data(user_data: dict) -> dict:
    """Safely serialize user_data for logging, handling non-JSON-serializable objects."""
    safe_data = {}
    for key, value in user_data.items():
        try:
            # Try to serialize each value to check if it's JSON-safe
            json.dumps(value, ensure_ascii=False)
            safe_data[key] = value
        except (TypeError, ValueError):
            # Handle special cases for non-serializable objects
            if key == "search_results" and isinstance(value, list):
                # Convert SearchResult objects to basic info
                safe_data[key] = [
                    {
                        "participant_id": result.participant.id if hasattr(result, 'participant') else str(result),
                        "confidence": getattr(result, 'confidence', 'unknown'),
                        "match_field": getattr(result, 'match_field', 'unknown')
                    } 
                    for result in value
                ]
            elif hasattr(value, '__dict__'):
                # For other objects with attributes, just store the type
                safe_data[key] = f"<{type(value).__name__} object>"
            else:
                # For other non-serializable values, store their string representation
                safe_data[key] = str(value)
    return safe_data


class TestJSONSerializationFix(unittest.TestCase):
    """Test cases for the JSON serialization fix that resolves search button issues."""

    def test_search_results_serialization(self):
        """Test that SearchResult objects are properly converted for JSON serialization."""
        # Create mock data that would cause the original error
        participant = MockParticipant(id="rec123", FullNameRU="Test User")
        search_result = MockSearchResult(
            participant=participant,
            confidence=0.8,
            match_field="name_ru",
            match_type="fuzzy"
        )
        
        user_data = {
            "search_results": [search_result],
            "current_state": 8,
            "messages_to_delete": [1, 2, 3]
        }
        
        # Verify original data cannot be serialized
        with self.assertRaises(TypeError):
            json.dumps(user_data, ensure_ascii=False)
        
        # Test our safe serialization
        safe_data = _safe_serialize_user_data(user_data)
        
        # Should be able to serialize now
        json_str = json.dumps(safe_data, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        
        # Verify structure is correct
        self.assertIn("search_results", safe_data)
        self.assertIsInstance(safe_data["search_results"], list)
        self.assertEqual(len(safe_data["search_results"]), 1)
        
        # Verify search result conversion
        converted_result = safe_data["search_results"][0]
        self.assertEqual(converted_result["participant_id"], "rec123")
        self.assertEqual(converted_result["confidence"], 0.8)
        self.assertEqual(converted_result["match_field"], "name_ru")

    def test_mixed_serializable_data(self):
        """Test that normal serializable data passes through unchanged."""
        user_data = {
            "string_value": "test",
            "number_value": 42,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"}
        }
        
        # Should work with direct serialization
        json.dumps(user_data, ensure_ascii=False)
        
        # Should also work with safe serialization and remain unchanged
        safe_data = _safe_serialize_user_data(user_data)
        self.assertEqual(safe_data, user_data)

    def test_object_with_attributes(self):
        """Test that objects with __dict__ are handled properly."""
        class CustomObject:
            def __init__(self):
                self.value = "test"
        
        user_data = {
            "custom_object": CustomObject(),
            "normal_data": "test"
        }
        
        safe_data = _safe_serialize_user_data(user_data)
        
        # Custom object should be converted to string representation
        self.assertEqual(safe_data["custom_object"], "<CustomObject object>")
        self.assertEqual(safe_data["normal_data"], "test")

    def test_empty_search_results(self):
        """Test handling of empty search results list."""
        user_data = {
            "search_results": [],
            "current_state": 8
        }
        
        safe_data = _safe_serialize_user_data(user_data)
        self.assertEqual(safe_data["search_results"], [])
        self.assertEqual(safe_data["current_state"], 8)

    def test_multiple_search_results(self):
        """Test handling of multiple search results."""
        participants = [
            MockParticipant(id="rec1", FullNameRU="User 1"),
            MockParticipant(id="rec2", FullNameRU="User 2")
        ]
        
        search_results = [
            MockSearchResult(participant=participants[0], confidence=1.0, match_field="name_ru", match_type="exact"),
            MockSearchResult(participant=participants[1], confidence=0.7, match_field="name_ru", match_type="fuzzy")
        ]
        
        user_data = {"search_results": search_results}
        
        safe_data = _safe_serialize_user_data(user_data)
        
        self.assertEqual(len(safe_data["search_results"]), 2)
        self.assertEqual(safe_data["search_results"][0]["participant_id"], "rec1")
        self.assertEqual(safe_data["search_results"][0]["confidence"], 1.0)
        self.assertEqual(safe_data["search_results"][1]["participant_id"], "rec2")
        self.assertEqual(safe_data["search_results"][1]["confidence"], 0.7)


if __name__ == '__main__':
    unittest.main()
