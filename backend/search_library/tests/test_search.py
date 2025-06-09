"""Tests for the search_library module."""

import pytest
from unittest.mock import Mock, patch
from typing import List, Tuple, Any

from ..search import search_library, recursive_search
from ..types import Song
from ..clients import LLMClient, TextPrompt, TextResult


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self, mock_responses: List[str]):
        self.mock_responses = mock_responses
        self.call_count = 0
    
    def generate(
        self,
        messages,
        max_tokens: int,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        tools=None,
        tool_choice=None,
        thinking_tokens: int | None = None,
    ) -> Tuple[List[TextResult], dict[str, Any]]:
        """Mock generate method that returns predefined responses."""
        if self.call_count < len(self.mock_responses):
            response = self.mock_responses[self.call_count]
            self.call_count += 1
            return ([TextResult(text=response)], {})
        else:
            return ([TextResult(text="")], {})


def create_test_songs(count: int, start_id: int = 1) -> List[Song]:
    """Create test songs for testing."""
    songs = []
    for i in range(count):
        song_id = start_id + i
        songs.append(Song(
            id=str(song_id),
            song_link=f"https://example.com/song{song_id}",
            song_metadata=f'{{"duration": {180 + i * 10}, "genre": "test", "release_year": 2020}}',
            lyrics=f"Test lyrics for song {song_id}",
            name=f"Test Song {song_id}",
            artist=f"Test Artist {song_id}"
        ))
    return songs


class TestSearchLibrary:
    """Test cases for search_library function."""

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_small_library(self, mock_decode, mock_get_query):
        """Test search_library with a small library (no chunking needed)."""
        # Setup
        test_songs = create_test_songs(5)
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = ["1", "3", "5"]
        
        mock_client = MockLLMClient(["1,3,5"])
        
        # Execute
        result = search_library(mock_client, test_songs, "test query", n=3)
        
        # Assert
        assert len(result) == 3
        assert result[0].id == "1"
        assert result[1].id == "3" 
        assert result[2].id == "5"
        mock_get_query.assert_called_once()
        mock_decode.assert_called_once_with("1,3,5")

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_large_library_chunking(self, mock_decode, mock_get_query):
        """Test search_library with a large library requiring chunking."""
        # Setup - create 2500 songs to force chunking (3 chunks of 1000 each)
        test_songs = create_test_songs(2500)
        mock_get_query.return_value = "mocked query"
        
        # Mock responses for each chunk + final filtering
        mock_decode.side_effect = [
            ["1", "2", "3"],  # First chunk results
            ["1001", "1002"],  # Second chunk results  
            ["2001"],  # Third chunk results
            ["1", "1001"]  # Final filtering results
        ]
        
        mock_client = MockLLMClient(["1,2,3", "1001,1002", "2001", "1,1001"])
        
        # Execute
        result = search_library(mock_client, test_songs, "test query", n=2)
        
        # Assert
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "1001"
        assert mock_get_query.call_count == 4  # 3 chunks + 1 final filtering
        assert mock_decode.call_count == 4

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_no_results(self, mock_decode, mock_get_query):
        """Test search_library when no songs match."""
        # Setup
        test_songs = create_test_songs(5)
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = []
        
        mock_client = MockLLMClient([""])
        
        # Execute
        result = search_library(mock_client, test_songs, "test query", n=3)
        
        # Assert
        assert len(result) == 0
        mock_get_query.assert_called_once()
        mock_decode.assert_called_once()

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_verbose_mode(self, mock_decode, mock_get_query):
        """Test search_library with verbose=True."""
        # Setup
        test_songs = create_test_songs(3)
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = ["1", "2"]
        
        mock_client = MockLLMClient(["1,2"])
        
        # Execute with verbose=True
        result = search_library(mock_client, test_songs, "test query", n=2, verbose=True)
        
        # Assert
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"


class TestRecursiveSearch:
    """Test cases for recursive_search function."""

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_recursive_search_basic(self, mock_decode, mock_get_query):
        """Test basic recursive_search functionality."""
        # Setup
        test_songs = create_test_songs(5)
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = ["2", "4"]
        
        mock_client = MockLLMClient(["2,4"])
        
        # Execute
        result = recursive_search(mock_client, test_songs, "test query", n=2)
        
        # Assert
        assert len(result) == 2
        assert result[0].id == "2"
        assert result[1].id == "4"
        mock_get_query.assert_called_once_with(test_songs, "test query", 2)

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_recursive_search_partial_match(self, mock_decode, mock_get_query):
        """Test recursive_search when some IDs don't match."""
        # Setup
        test_songs = create_test_songs(3)  # IDs: 1, 2, 3
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = ["1", "999", "3"]  # 999 doesn't exist
        
        mock_client = MockLLMClient(["1,999,3"])
        
        # Execute
        result = recursive_search(mock_client, test_songs, "test query", n=3)
        
        # Assert - should only return matching songs
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "3"

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_recursive_search_empty_library(self, mock_decode, mock_get_query):
        """Test recursive_search with empty library."""
        # Setup
        test_songs = []
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = []
        
        mock_client = MockLLMClient([""])
        
        # Execute
        result = recursive_search(mock_client, test_songs, "test query", n=3)
        
        # Assert
        assert len(result) == 0
        mock_get_query.assert_called_once_with([], "test query", 3)

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_recursive_search_verbose_output(self, mock_decode, mock_get_query, capsys):
        """Test recursive_search verbose output."""
        # Setup
        test_songs = create_test_songs(2)
        mock_get_query.return_value = "test prompt"
        mock_decode.return_value = ["1"]
        
        mock_client = MockLLMClient(["response text"])
        
        # Execute with verbose=True
        result = recursive_search(mock_client, test_songs, "test query", n=1, verbose=True)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == "1"


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_exact_chunk_boundary(self, mock_decode, mock_get_query):
        """Test search_library with exactly 1000 songs (boundary case)."""
        # Setup
        test_songs = create_test_songs(1000)
        mock_get_query.return_value = "mocked query"
        mock_decode.return_value = ["1", "500", "1000"]
        
        mock_client = MockLLMClient(["1,500,1000"])
        
        # Execute
        result = search_library(mock_client, test_songs, "test query", n=3)
        
        # Assert - should not trigger second round of filtering
        assert len(result) == 3
        assert mock_get_query.call_count == 1  # Only one chunk

    @patch('backend.search_library.search.get_basic_query')
    @patch('backend.search_library.search.decode_assistant_response')
    def test_search_library_multiple_chunks_exact_n(self, mock_decode, mock_get_query):
        """Test search_library where chunking returns exactly n results."""
        # Setup
        test_songs = create_test_songs(1500)  # 2 chunks
        mock_get_query.return_value = "mocked query"
        mock_decode.side_effect = [
            ["1", "2"],  # First chunk: 2 results
            ["1001"],    # Second chunk: 1 result
            # Total: 3 results, exactly n=3, so no second filtering needed
        ]
        
        mock_client = MockLLMClient(["1,2", "1001"])
        
        # Execute
        result = search_library(mock_client, test_songs, "test query", n=3)
        
        # Assert
        assert len(result) == 3
        assert mock_get_query.call_count == 2  # 2 chunks, no additional filtering


if __name__ == "__main__":
    pytest.main([__file__]) 