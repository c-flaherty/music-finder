# Music Finder

A full-stack music search application with a Next.js frontend and Python backend API (using Vercel), integrated with Supabase for data storage. Enables a user to search over their Spotify playlists with requests like "What was that song about kissing on a roof in New York? It had like a 90s vibe."

## Prerequisites

- Node.js (v18 or higher)
- Python (v3.8 or higher)
- Poetry
- npm or yarn
- Supabase + Vercel credentials

## Project Structure

```
music-finder/
├── frontend/music-finder/     # Next.js frontend application
├── backend/                   # Python backend API
├── env1/                     # Python virtual environment
└── README.md
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd music-finder
```

### 2. Backend Setup

#### Setup virtual env

```bash
poetry install
poetry env activate
```
Run the command that is output to activate the environment.

#### Link to vercel

```
npm install -g vercel
vercel login
vercel link --project="music-finder"
```

#### Environment Variables

The environment variables are stored in Vercel. Linking to Vercel will set them up. Confirm that they are configured correctly with:
```
vercel env ls
```

Also, you probably want to pull them locally for experimentation purposes. Run this from root directory.
```
vercel env pull .env.local
```

### 3. Frontend Setup

TODO

## Running the Application

### Start the Backend (Development)

Run from root directory:
```bash
npx vercel dev --debug
```

### Start the Frontend (Development)

TODO 

## API Endpoints

The backend provides the following API endpoints:

- `POST /api/update-table` - Insert music data into Supabase tables
- `POST /api/sync-user` - onboard or update userdata
  - TODO: Not implemented at all
- `GET /api/hello-world` - Test endpoint
- `POST /api/search-songs` - Search for songs based on a natural language query
  - TODO: Add user authentication to search over user's songs only

### Example API Usage

For `update-table`:
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

For `search-songs`:
```
curl -X POST http://localhost:3000/api/search-songs   -H "Content-Type: application/json"   -d '{
    "query": "any song will do"
  }'
```