"""Chess API for Vercel deployment with Upstash Redis storage."""
import json
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import chess_logic
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from upstash_redis import Redis
import chess
from chess_logic import (
    NewGameRequest, MoveRequest, GameState, GameSummary, 
    MoveResponse, NewGameResponse, GamesListResponse,
    get_current_player, get_game_status, create_game_data, validate_and_make_move
)

app = FastAPI(title="Chess API", description="Bot-vs-bot chess games API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
# Vercel+Upstash integration uses KV_REST_API_* env vars;
# upstash-redis SDK expects UPSTASH_REDIS_REST_* — map if needed.
for src, dst in [("KV_REST_API_URL", "UPSTASH_REDIS_REST_URL"), ("KV_REST_API_TOKEN", "UPSTASH_REDIS_REST_TOKEN")]:
    if src in os.environ and dst not in os.environ:
        os.environ[dst] = os.environ[src]

try:
    redis = Redis.from_env()
except KeyError:
    redis = None

# Storage functions for Redis
def save_game(game_data: dict) -> None:
    """Save game data to Redis"""
    if redis is None:
        raise RuntimeError("Redis not configured - set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables")
    game_id = game_data["id"]
    redis.set(f"game:{game_id}", json.dumps(game_data))
    redis.sadd("games:all", game_id)

def load_game(game_id: str) -> dict | None:
    """Load game data from Redis"""
    if redis is None:
        raise RuntimeError("Redis not configured - set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables")
    data = redis.get(f"game:{game_id}")
    if data is None:
        return None
    return json.loads(data)

def list_all_games() -> list[dict]:
    """List all games from Redis"""
    if redis is None:
        raise RuntimeError("Redis not configured - set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables")
    game_ids = redis.smembers("games:all")
    games = []
    
    for game_id in game_ids:
        game_data = load_game(game_id)
        if game_data:
            games.append(game_data)
    
    return games

# API Endpoints
@app.post("/game/new", response_model=NewGameResponse)
async def create_new_game(request: NewGameRequest):
    """Create a new chess game"""
    game_data = create_game_data(request)
    save_game(game_data)
    
    return NewGameResponse(
        game_id=game_data["id"],
        white=request.white,
        black=request.black,
        status="in_progress",
        current_player=request.white,  # white always goes first
        fen=game_data["fen"],
        moves=[]
    )

@app.get("/game/{game_id}", response_model=GameState)
async def get_game_state(game_id: str):
    """Get current game state"""
    game_data = load_game(game_id)
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    board = chess.Board(game_data["fen"])
    current_player = get_current_player(board, game_data["white"], game_data["black"])
    
    return GameState(
        id=game_data["id"],
        white=game_data["white"],
        black=game_data["black"],
        fen=game_data["fen"],
        moves=game_data["moves"],
        status=game_data["status"],
        current_player=current_player,
        created_at=game_data["created_at"],
        updated_at=game_data["updated_at"]
    )

@app.post("/game/{game_id}/move", response_model=MoveResponse)
async def make_move(game_id: str, request: MoveRequest):
    """Make a move in the game"""
    game_data = load_game(game_id)
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    try:
        updated_game_data = validate_and_make_move(game_data, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    save_game(updated_game_data)
    
    board = chess.Board(updated_game_data["fen"])
    new_current_player = get_current_player(board, updated_game_data["white"], updated_game_data["black"])
    
    return MoveResponse(
        move=request.move,
        status=updated_game_data["status"],
        current_player=new_current_player,
        moves=updated_game_data["moves"],
        fen=updated_game_data["fen"]
    )

@app.get("/game/{game_id}/board")
async def get_board_ascii(game_id: str):
    """Get ASCII representation of the board"""
    game_data = load_game(game_id)
    if not game_data:
        raise HTTPException(status_code=404, detail="Game not found")
    
    board = chess.Board(game_data["fen"])
    return str(board)

@app.get("/games", response_model=GamesListResponse)
async def list_games():
    """List all games"""
    games_data = list_all_games()
    games = []
    
    for game_data in games_data:
        games.append(GameSummary(
            id=game_data["id"],
            white=game_data["white"],
            black=game_data["black"],
            status=game_data["status"],
            created_at=game_data["created_at"]
        ))
    
    return GamesListResponse(games=games)