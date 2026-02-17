"""Shared chess game logic and models."""
from pydantic import BaseModel
import chess
import uuid
from datetime import datetime
from typing import List, Optional

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

def create_game_data(request: NewGameRequest) -> dict:
    """Create initial game data from a new game request"""
    game_id = str(uuid.uuid4())
    board = chess.Board()
    current_time = datetime.utcnow().isoformat()
    
    return {
        "id": game_id,
        "white": request.white,
        "black": request.black,
        "fen": board.fen(),
        "moves": [],
        "status": "in_progress",
        "created_at": current_time,
        "updated_at": current_time
    }

def validate_and_make_move(game_data: dict, request: MoveRequest) -> dict:
    """Validate and make a move, returning updated game data"""
    board = chess.Board(game_data["fen"])
    
    # Check if it's the player's turn
    current_player = get_current_player(board, game_data["white"], game_data["black"])
    if request.player != current_player:
        raise ValueError("Not your turn")
    
    # Validate and make the move
    try:
        move = chess.Move.from_uci(request.move)
        if move not in board.legal_moves:
            raise ValueError("Invalid move")
        
        board.push(move)
    except ValueError as e:
        if "Invalid move" in str(e):
            raise ValueError("Invalid move")
        else:
            raise ValueError("Invalid move format")
    
    # Update game data
    game_data["fen"] = board.fen()
    game_data["moves"].append(request.move)
    game_data["status"] = get_game_status(board)
    game_data["updated_at"] = datetime.utcnow().isoformat()
    
    return game_data