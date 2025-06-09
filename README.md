# Music Finder

Checkout https://docs.google.com/document/d/1diwqL13toAnHAhgHHUHn97VsaX-cERfuJVjhuxajbMk/edit?usp=sharing 

### Supabase integration

test command for updating table:
```
curl -X POST http://localhost:3000/api/update-table   -H "Content-Type: application/json"   -d '{
    "tableName": "songs",
    "data": [
      {
        "song_link": "https://spotify.com/track/example123",
        "song_metadata": "{\"duration\": 180, \"genre\": \"pop\", \"release_year\": 2023}",
        "lyrics": "Example lyrics of the first song...",
        "name": "First Song",
        "artist": "Artist One"
      },
      {
        "song_link": "https://youtube.com/watch?v=example456",
        "song_metadata": "{\"duration\": 240, \"genre\": \"rock\", \"release_year\": 2022}",
        "lyrics": "Example lyrics of the second song...",
        "name": "Second Song",
        "artist": "Artist Two"
      }
    ]
  }'
```