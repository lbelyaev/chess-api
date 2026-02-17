# Chess API

A lightweight REST API for bot-vs-bot chess games, built for Discord bots Jarvis and Gromozeka.

## Features

- Create new chess games between two players
- Make moves with full chess rule validation
- Get current game state and board representation
- ASCII board display for Discord posting
- Game state persistence via JSON files
- Support for checkmate, stalemate, and draw detection

## Installation

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

## Running the Server

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8888
```

The API will be available at `http://localhost:8888`

## API Documentation

Once the server is running, visit:
- Interactive API docs: `http://localhost:8888/docs`
- ReDoc documentation: `http://localhost:8888/redoc`

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

## Game Storage

Games are stored as JSON files in `~/.chess-api/games/` directory. Each game file is named `{game_id}.json` and contains:

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

Run the test suite:

```bash
source venv/bin/activate
python -m pytest test_chess_api.py -v
```

## CORS

CORS is enabled for all origins to allow Discord bots from different hosts to access the API.

## Tech Stack

- **Python 3.12+** - Runtime
- **FastAPI** - Web framework
- **python-chess** - Chess logic and validation
- **uvicorn** - ASGI server
- **pytest** - Testing framework

## Development

The project follows Test-Driven Development (TDD). All tests are in `test_chess_api.py` and should pass before any changes are committed.

To make changes:
1. Write or update tests first
2. Implement the feature to make tests pass
3. Verify all tests still pass
4. Commit changes

## Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid move, wrong turn, etc.)
- `404` - Game not found
- `500` - Server error

Error responses include descriptive messages in the `detail` field.