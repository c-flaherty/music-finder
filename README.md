# Music Finder

A full-stack music search application with a Next.js frontend and Python backend API, integrated with Supabase for data storage.

## Prerequisites

- Node.js (v18 or higher)
- Python (v3.8 or higher)
- npm or yarn
- Supabase account

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

#### Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv env1

# Activate virtual environment
# On macOS/Linux:
source env1/bin/activate
# On Windows:
# env1\Scripts\activate
```

#### Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# API Keys (if using AI features)
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 3. Frontend Setup

```bash
cd frontend/music-finder
npm install
```

### 4. Supabase Setup

1. Create a new project on [Supabase](https://supabase.com)
2. Get your project URL and service role key from the project settings
3. Create the necessary tables in your Supabase database:

```sql
CREATE TABLE songs (
  id SERIAL PRIMARY KEY,
  song_link TEXT,
  song_metadata TEXT,
  lyrics TEXT,
  name TEXT NOT NULL,
  artist TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Running the Application

### Start the Backend (Development)

```bash
# Make sure you're in the backend directory and virtual environment is activated
cd backend
# The backend APIs are deployed on Vercel and can be tested locally using Vercel CLI
vercel dev
```

### Start the Frontend (Development)

```bash
cd frontend/music-finder
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

The backend provides the following API endpoints:

- `POST /api/update-table` - Insert music data into Supabase tables
- `GET /api/hello-world` - Test endpoint
- `POST /api/search-songs` - Search for songs (if implemented)

### Example API Usage

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