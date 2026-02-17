# Chess API

A lightweight REST API for bot-vs-bot chess games, built for Discord bots Jarvis and Gromozeka. Supports both local development (JSON files) and Vercel serverless deployment (Upstash Redis).

## Features

- Create new chess games between two players
- Make moves with full chess rule validation
- Get current game state and board representation
- ASCII board display for Discord posting
- Game state persistence via JSON files (local) or Redis (Vercel)
- Support for checkmate, stalemate, and draw detection

## Deployment Options

### Option 1: Vercel + Upstash Redis (Production)

This API is designed for serverless deployment on Vercel with Upstash Redis for storage.

#### Prerequisites
1. **Vercel account** - Sign up at [vercel.com](https://vercel.com)
2. **Upstash Redis database** - Create a free Redis database at [upstash.com](https://console.upstash.com/redis)

#### Setting up Upstash Redis
1. Go to [Upstash Console](https://console.upstash.com/redis)
2. Create a new Redis database (free tier available)
3. Copy the **REST URL** and **REST TOKEN** from the database details
4. These will be your environment variables

#### Deploy to Vercel
1. Fork/clone this repository
2. Connect your repository to Vercel
3. Set environment variables in Vercel:
   - `UPSTASH_REDIS_REST_URL` = Your Redis REST URL
   - `UPSTASH_REDIS_REST_TOKEN` = Your Redis REST token
4. Deploy! Vercel will automatically detect the `vercel.json` configuration

The API will be available at your Vercel domain (e.g., `https://your-app.vercel.app`)

#### Environment Variables for Vercel
```
UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-redis-token
```

### Option 2: Local Development

For local development and testing, the original JSON file storage is still supported.

#### Installation
1. Clone or download this directory
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Running the Server Locally
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8888
```

The API will be available at `http://localhost:8888`

## API Documentation

Once the server is running, visit:
- Interactive API docs: `http://localhost:8888/docs` (local) or `https://your-app.vercel.app/docs` (Vercel)
- ReDoc documentation: `http://localhost:8888/redoc` (local) or `https://your-app.vercel.app/redoc` (Vercel)

## API Endpoints

### Create New Game
```http
POST /game/new
Content-Type: application/json

{
  "white": "jarvis",
  "black": "gromozeka"
}
```

Returns game ID and initial state.

### Get Game State
```http
GET /game/{game_id}
```

Returns current game state including FEN, moves, status, and whose turn it is.

### Make a Move
```http
POST /game/{game_id}/move
Content-Type: application/json

{
  "player": "jarvis",
  "move": "e2e4"
}
```

Move format is UCI notation (e.g., "e2e4", "g1f3", "e7e8q" for promotion).

### Get Board ASCII
```http
GET /game/{game_id}/board
```

Returns ASCII art representation of the current board position.

### List All Games
```http
GET /games
```

Returns summary of all games (active and completed).

## Game States

- `in_progress` - Game is ongoing
- `checkmate` - Game ended by checkmate
- `stalemate` - Game ended by stalemate
- `draw` - Game ended by other draw conditions (insufficient material, repetition, etc.)

## Storage

### Local Development (JSON Files)
Games are stored as JSON files in `~/.chess-api/games/` directory. Each game file is named `{game_id}.json`.

### Vercel Production (Redis)
Games are stored in Upstash Redis with the following structure:
- Game data: `game:{game_id}` → JSON string
- Game list: `games:all` → Redis set containing all game IDs

Both storage methods maintain the same game data format:
```json
{
  "id": "uuid",
  "white": "player_name",
  "black": "player_name", 
  "fen": "current_board_position",
  "moves": ["list", "of", "uci", "moves"],
  "status": "in_progress",
  "created_at": "iso_timestamp",
  "updated_at": "iso_timestamp"
}
```

## Testing

### Local Tests (JSON storage)
```bash
source venv/bin/activate
python -m pytest test_chess_api.py -v
```

### Vercel Tests (Redis storage - mocked)
```bash
source venv/bin/activate
python -m pytest test_chess_api_redis.py -v
```

## CORS

CORS is enabled for all origins to allow Discord bots from different hosts to access the API.

## Tech Stack

- **Python 3.12+** - Runtime
- **FastAPI** - Web framework
- **python-chess** - Chess logic and validation
- **upstash-redis** - Redis client for Vercel (serverless-friendly)
- **uvicorn** - ASGI server (local development)
- **pytest** - Testing framework

## Architecture

The project is structured for both local development and serverless deployment:

- `main.py` - Local development server with JSON file storage
- `api/index.py` - Vercel serverless function with Redis storage
- `chess_logic.py` - Shared game logic and models
- `vercel.json` - Vercel deployment configuration

## Development

The project follows Test-Driven Development (TDD). All tests should pass before any changes are committed.

To make changes:
1. Write or update tests first
2. Implement the feature to make tests pass
3. Verify all tests still pass (both local and Redis versions)
4. Commit changes

## Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid move, wrong turn, etc.)
- `404` - Game not found
- `500` - Server error

Error responses include descriptive messages in the `detail` field.

## Costs

- **Local development**: Free
- **Vercel deployment**: Free tier supports hobby projects
- **Upstash Redis**: Free tier includes 10K commands/day, perfect for testing

Both platforms offer generous free tiers suitable for Discord bot usage.