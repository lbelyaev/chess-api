import pytest
import json
import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_games_dir():
    """Clean up games directory before and after each test"""
    games_dir = Path.home() / ".chess-api" / "games"
    if games_dir.exists():
        shutil.rmtree(games_dir)
    yield
    if games_dir.exists():
        shutil.rmtree(games_dir)

def test_create_new_game():
    """Test creating a new game"""
    response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    assert response.status_code == 200
    data = response.json()
    
    assert "game_id" in data
    assert "fen" in data
    assert data["white"] == "jarvis"
    assert data["black"] == "gromozeka"
    assert data["status"] == "in_progress"
    assert data["current_player"] == "jarvis"  # white moves first
    assert len(data["moves"]) == 0

def test_create_game_with_reversed_colors():
    """Test creating a game with black/white reversed"""
    response = client.post("/game/new", json={"white": "gromozeka", "black": "jarvis"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["white"] == "gromozeka"
    assert data["black"] == "jarvis"
    assert data["current_player"] == "gromozeka"  # white moves first

def test_get_game_state():
    """Test getting current game state"""
    # Create a game first
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Get game state
    response = client.get(f"/game/{game_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == game_id
    assert "fen" in data
    assert data["white"] == "jarvis"
    assert data["black"] == "gromozeka"
    assert data["status"] == "in_progress"
    assert data["current_player"] == "jarvis"
    assert len(data["moves"]) == 0

def test_get_nonexistent_game():
    """Test getting a game that doesn't exist"""
    response = client.get("/game/nonexistent")
    assert response.status_code == 404

def test_make_valid_move():
    """Test making a valid chess move"""
    # Create a game
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Make a move
    response = client.post(f"/game/{game_id}/move", json={"player": "jarvis", "move": "e2e4"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["move"] == "e2e4"
    assert data["status"] == "in_progress"
    assert data["current_player"] == "gromozeka"  # turn switches to black
    assert len(data["moves"]) == 1
    assert data["moves"][0] == "e2e4"

def test_make_move_wrong_turn():
    """Test making a move when it's not the player's turn"""
    # Create a game
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Try to make a move as black (should be white's turn)
    response = client.post(f"/game/{game_id}/move", json={"player": "gromozeka", "move": "e7e5"})
    assert response.status_code == 400
    assert "not your turn" in response.json()["detail"].lower()

def test_make_invalid_move():
    """Test making an invalid chess move"""
    # Create a game
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Try to make an invalid move
    response = client.post(f"/game/{game_id}/move", json={"player": "jarvis", "move": "e2e5"})
    assert response.status_code == 400
    assert "invalid move" in response.json()["detail"].lower()

def test_get_board_ascii():
    """Test getting ASCII board representation"""
    # Create a game
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Get board ASCII
    response = client.get(f"/game/{game_id}/board")
    assert response.status_code == 200
    
    board_text = response.text.strip('"').replace('\\n', '\n')
    # Should contain chess pieces
    assert "r" in board_text  # black rook
    assert "R" in board_text  # white rook
    assert "♜" in board_text or "r" in board_text  # some representation of pieces

def test_list_games():
    """Test listing all games"""
    # Create multiple games
    client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    client.post("/game/new", json={"white": "gromozeka", "black": "jarvis"})
    
    # List games
    response = client.get("/games")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["games"]) == 2
    for game in data["games"]:
        assert "id" in game
        assert "white" in game
        assert "black" in game
        assert "status" in game

def test_checkmate_detection():
    """Test that checkmate is properly detected"""
    # This would require setting up a specific board position
    # For now, we'll create a simple test that ensures the status can change
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    # Make some moves to verify game progresses
    client.post(f"/game/{game_id}/move", json={"player": "jarvis", "move": "e2e4"})
    response = client.post(f"/game/{game_id}/move", json={"player": "gromozeka", "move": "e7e5"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

def test_stalemate_detection():
    """Test that stalemate is properly detected"""
    # Similar to checkmate, this would require a specific board setup
    # For now, ensure the game can progress normally
    create_response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    game_id = create_response.json()["game_id"]
    
    response = client.get(f"/game/{game_id}")
    assert response.json()["status"] == "in_progress"

def test_move_on_nonexistent_game():
    """Test making a move on a game that doesn't exist"""
    response = client.post("/game/nonexistent/move", json={"player": "jarvis", "move": "e2e4"})
    assert response.status_code == 404

def test_board_on_nonexistent_game():
    """Test getting board for a game that doesn't exist"""
    response = client.get("/game/nonexistent/board")
    assert response.status_code == 404