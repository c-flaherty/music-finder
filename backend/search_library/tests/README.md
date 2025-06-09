# Search Library Tests

This directory contains comprehensive tests for the `search_library` module.

## Test Files

- `test_search.py` - Tests for the main search functionality including `search_library()` and `recursive_search()` functions

## Test Coverage

The tests cover:

### `search_library()` function:
- Small libraries (no chunking needed)
- Large libraries requiring chunking (>1000 songs)
- Multiple chunks with second round filtering
- Edge cases (exact chunk boundaries, exact result counts)
- No results scenarios
- Verbose mode

### `recursive_search()` function:
- Basic functionality 
- Partial ID matches (some IDs don't exist in library)
- Empty library handling
- Verbose output

### Edge Cases:
- Boundary conditions (exactly 1000 songs)
- Multiple chunks returning exactly `n` results
- Invalid song IDs in responses

## Running Tests

### Run all tests:
```bash
# From the backend directory
python -m pytest search_library/tests/
```

## Test Dependencies

The tests use mocking to avoid dependencies on:
- Actual LLM API calls
- External services
- Specific prompt generation logic

## Mock Objects

- `MockLLMClient` - Simulates LLM responses with predefined text
- `create_test_songs()` - Helper function to generate test Song objects

This ensures tests run quickly and reliably without external dependencies. 