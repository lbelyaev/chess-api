"""Tests for the chess API with Redis storage (mocked)."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock Redis before importing the API
with patch('upstash_redis.Redis.from_env'):
    from api.index import app

client = TestClient(app)

@pytest.fixture
def mock_redis():
    """Mock Redis client for tests"""
    mock = Mock()
    mock.get = Mock(return_value=None)
    mock.set = Mock()
    mock.sadd = Mock()
    mock.smembers = Mock(return_value=set())
    return mock

@pytest.fixture(autouse=True)
def patch_redis(mock_redis):
    """Auto-patch Redis for all tests"""
    with patch('api.index.redis', mock_redis):
        yield mock_redis

def test_create_new_game(mock_redis):
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
    
    # Verify Redis calls
    mock_redis.set.assert_called_once()
    mock_redis.sadd.assert_called_once()

def test_create_game_with_reversed_colors(mock_redis):
    """Test creating a game with black/white reversed"""
    response = client.post("/game/new", json={"white": "gromozeka", "black": "jarvis"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["white"] == "gromozeka"
    assert data["black"] == "jarvis"
    assert data["current_player"] == "gromozeka"  # white moves first

def test_get_game_state(mock_redis):
    """Test getting current game state"""
    # Mock game data
    game_data = {
        "id": "test-game-id",
        "white": "jarvis",
        "black": "gromozeka",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }
    mock_redis.get.return_value = json.dumps(game_data)
    
    response = client.get("/game/test-game-id")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == "test-game-id"
    assert "fen" in data
    assert data["white"] == "jarvis"
    assert data["black"] == "gromozeka"
    assert data["status"] == "in_progress"
    assert data["current_player"] == "jarvis"
    assert len(data["moves"]) == 0

def test_get_nonexistent_game(mock_redis):
    """Test getting a game that doesn't exist"""
    mock_redis.get.return_value = None
    
    response = client.get("/game/nonexistent")
    assert response.status_code == 404

def test_make_valid_move(mock_redis):
    """Test making a valid chess move"""
    # Mock game data
    game_data = {
        "id": "test-game-id",
        "white": "jarvis",
        "black": "gromozeka",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }
    mock_redis.get.return_value = json.dumps(game_data)
    
    # Make a move
    response = client.post("/game/test-game-id/move", json={"player": "jarvis", "move": "e2e4"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["move"] == "e2e4"
    assert data["status"] == "in_progress"
    assert data["current_player"] == "gromozeka"  # turn switches to black
    assert len(data["moves"]) == 1
    assert data["moves"][0] == "e2e4"
    
    # Verify Redis was called to save the updated game
    assert mock_redis.set.call_count >= 1

def test_make_move_wrong_turn(mock_redis):
    """Test making a move when it's not the player's turn"""
    # Mock game data (white's turn)
    game_data = {
        "id": "test-game-id",
        "white": "jarvis",
        "black": "gromozeka",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }
    mock_redis.get.return_value = json.dumps(game_data)
    
    # Try to make a move as black (should be white's turn)
    response = client.post("/game/test-game-id/move", json={"player": "gromozeka", "move": "e7e5"})
    assert response.status_code == 400
    assert "not your turn" in response.json()["detail"].lower()

def test_make_invalid_move(mock_redis):
    """Test making an invalid chess move"""
    # Mock game data
    game_data = {
        "id": "test-game-id",
        "white": "jarvis",
        "black": "gromozeka",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }
    mock_redis.get.return_value = json.dumps(game_data)
    
    # Try to make an invalid move
    response = client.post("/game/test-game-id/move", json={"player": "jarvis", "move": "e2e5"})
    assert response.status_code == 400
    assert "invalid move" in response.json()["detail"].lower()

def test_get_board_ascii(mock_redis):
    """Test getting ASCII board representation"""
    # Mock game data
    game_data = {
        "id": "test-game-id",
        "white": "jarvis",
        "black": "gromozeka",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "moves": [],
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }
    mock_redis.get.return_value = json.dumps(game_data)
    
    # Get board ASCII
    response = client.get("/game/test-game-id/board")
    assert response.status_code == 200
    
    board_text = response.text.strip('"').replace('\\n', '\n')
    # Should contain chess pieces
    assert "r" in board_text  # black rook
    assert "R" in board_text  # white rook

def test_list_games(mock_redis):
    """Test listing all games"""
    # Mock Redis returning game IDs
    mock_redis.smembers.return_value = {"game1", "game2"}
    
    # Mock game data for each ID
    game1_data = {
        "id": "game1",
        "white": "jarvis",
        "black": "gromozeka",
        "status": "in_progress",
        "created_at": "2023-01-01T00:00:00"
    }
    game2_data = {
        "id": "game2",
        "white": "gromozeka",
        "black": "jarvis",
        "status": "checkmate",
        "created_at": "2023-01-01T01:00:00"
    }
    
    def mock_get(key):
        if key == "game:game1":
            return json.dumps(game1_data)
        elif key == "game:game2":
            return json.dumps(game2_data)
        return None
    
    mock_redis.get.side_effect = mock_get
    
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

def test_list_games_empty(mock_redis):
    """Test listing games when none exist"""
    mock_redis.smembers.return_value = set()
    
    response = client.get("/games")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["games"]) == 0

def test_move_on_nonexistent_game(mock_redis):
    """Test making a move on a game that doesn't exist"""
    mock_redis.get.return_value = None
    
    response = client.post("/game/nonexistent/move", json={"player": "jarvis", "move": "e2e4"})
    assert response.status_code == 404

def test_board_on_nonexistent_game(mock_redis):
    """Test getting board for a game that doesn't exist"""
    mock_redis.get.return_value = None
    
    response = client.get("/game/nonexistent/board")
    assert response.status_code == 404

def test_redis_games_set_maintained(mock_redis):
    """Test that the games:all Redis set is properly maintained"""
    response = client.post("/game/new", json={"white": "jarvis", "black": "gromozeka"})
    assert response.status_code == 200
    game_id = response.json()["game_id"]
    
    # Verify sadd was called with the game ID
    mock_redis.sadd.assert_called_with("games:all", game_id)