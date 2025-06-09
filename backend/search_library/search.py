from .prompts import get_basic_query, decode_assistant_response
from .types import Song
from .clients import LLMClient, TextPrompt

def search_library(client: LLMClient, library: list[Song], user_query: str, n: int = 3, verbose: bool = False) -> list[Song]:
    prompt = get_basic_query(library, user_query, n)

    if verbose:
        print("PROMPT")
        print(prompt)
    
    # The generate method expects list[list[GeneralContentBlock]]
    # So we need to wrap the TextPrompt in another list
    response_tuple = client.generate(
        [[TextPrompt(text=prompt)]],  # Note the double brackets
        max_tokens=1000
    )
    
    # response_tuple is (list[AssistantContentBlock], dict)
    # We want the first AssistantContentBlock's text
    response_blocks = response_tuple[0]  # This is list[AssistantContentBlock]
    first_block = response_blocks[0]     # This is the first AssistantContentBlock
    response_text = first_block.text     # This is the text content
    
    if verbose:
        print("RESPONSE TEXT")
        print(response_text)

    song_ids = decode_assistant_response(response_text)

    if verbose:
        print("SONG IDS")
        print(song_ids)

        print("SONGS")
        print([song for song in library if song.id in song_ids])

    return [song for song in library if song.id in song_ids]
    
    