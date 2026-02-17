from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import chess.engine
import json
import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="Chess API", description="Bot-vs-bot chess games API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class NewGameRequest(BaseModel):
    white: str
    black: str

class MoveRequest(BaseModel):
    player: str
    move: str

class GameState(BaseModel):
    id: str
    white: str
    black: str
    fen: str
    moves: List[str]
    status: str
    current_player: str
    created_at: str
    updated_at: str

class GameSummary(BaseModel):
    id: str
    white: str
    black: str
    status: str
    created_at: str

class MoveResponse(BaseModel):
    move: str
    status: str
    current_player: str
    moves: List[str]
    fen: str

class NewGameResponse(BaseModel):
    game_id: str
    white: str
    black: str
    status: str
    current_player: str
    fen: str
    moves: List[str]

class GamesListResponse(BaseModel):
    games: List[GameSummary]

# Utility functions
def get_games_dir() -> Path:
    """Get the games directory path"""
    games_dir = Path.home() / ".chess-api" / "games"
    games_dir.mkdir(parents=True, exist_ok=True)
    return games_dir

def save_game(game_data: dict) -> None:
    """Save game data to JSON file"""
    games_dir = get_games_dir()
    game_file = games_dir / f"{game_data['id']}.json"
    with open(game_file, 'w') as f:
        json.dump(game_data, f, indent=2)

def load_game(game_id: str) -> Optional[dict]:
    """Load game data from JSON file"""
    games_dir = get_games_dir()
    game_file = games_dir / f"{game_id}.json"
    if not game_file.exists():
        return None
    with open(game_file, 'r') as f:
        return json.load(f)

def get_current_player(board: chess.Board, white_player: str, black_player: str) -> str:
    """Get the current player based on whose turn it is"""
    return white_player if board.turn == chess.WHITE else black_player

def get_game_status(board: chess.Board) -> str:
    """Determine the game status based on board state"""
    if board.is_checkmate():
        return "checkmate"
    elif board.is_stalemate():
        return "stalemate"
    elif board.is_insufficient_material():
        return "draw"
    elif board.is_fivefold_repetition():
        return "draw"
    elif board.is_seventyfive_moves():
        return "draw"
    else:
        return "in_progress"

# API Endpoints
@app.post("/game/new", response_model=NewGameResponse)
async def create_new_game(request: NewGameRequest):
    """Create a new chess game"""
    game_id = str(uuid.uuid4())
    board = chess.Board()
    current_time = datetime.utcnow().isoformat()
    
    game_data = {
        "id": game_id,
        "white": request.white,
        "black": request.black,
        "fen": board.fen(),
        "moves": [],
        "status": "in_progress",
        "created_at": current_time,
        "updated_at": current_time
    }
    
    save_game(game_data)
    
    return NewGameResponse(
        game_id=game_id,
        white=request.white,
        black=request.black,
        status="in_progress",
        current_player=request.white,  # white always goes first
        fen=board.fen(),
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
    
    board = chess.Board(game_data["fen"])
    
    # Check if it's the player's turn
    current_player = get_current_player(board, game_data["white"], game_data["black"])
    if request.player != current_player:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    # Validate and make the move
    try:
        move = chess.Move.from_uci(request.move)
        if move not in board.legal_moves:
            raise HTTPException(status_code=400, detail="Invalid move")
        
        board.push(move)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid move format")
    
    # Update game data
    game_data["fen"] = board.fen()
    game_data["moves"].append(request.move)
    game_data["status"] = get_game_status(board)
    game_data["updated_at"] = datetime.utcnow().isoformat()
    
    save_game(game_data)
    
    new_current_player = get_current_player(board, game_data["white"], game_data["black"])
    
    return MoveResponse(
        move=request.move,
        status=game_data["status"],
        current_player=new_current_player,
        moves=game_data["moves"],
        fen=game_data["fen"]
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
    games_dir = get_games_dir()
    games = []
    
    for game_file in games_dir.glob("*.json"):
        with open(game_file, 'r') as f:
            game_data = json.load(f)
            games.append(GameSummary(
                id=game_data["id"],
                white=game_data["white"],
                black=game_data["black"],
                status=game_data["status"],
                created_at=game_data["created_at"]
            ))
    
    return GamesListResponse(games=games)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)