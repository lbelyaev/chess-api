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
from fastapi.responses import HTMLResponse
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

CHESS_VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>♟ Jarvis vs Gromozeka — Live Chess</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #1e1f22;
      color: #dcddde;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px 16px 40px;
    }

    header {
      text-align: center;
      margin-bottom: 24px;
    }
    header h1 {
      font-size: 1.5rem;
      color: #fff;
      font-weight: 700;
    }
    header .subtitle {
      color: #b9bbbe;
      font-size: 0.875rem;
      margin-top: 4px;
    }

    .game-container {
      display: flex;
      gap: 24px;
      align-items: flex-start;
      width: 100%;
      max-width: 860px;
    }

    /* ── Player bars ── */
    .board-section { flex-shrink: 0; }

    .player-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      background: #2b2d31;
      border-radius: 8px;
      margin-bottom: 6px;
      border: 1px solid transparent;
      transition: border-color 0.3s, background 0.3s;
    }
    .player-bar.bottom { margin-bottom: 0; margin-top: 6px; }
    .player-bar.active {
      background: #2e3440;
      border-color: #5865f2;
    }
    .player-avatar {
      width: 32px; height: 32px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.2rem;
    }
    .player-avatar.white { background: #f0d9b5; }
    .player-avatar.black { background: #2d1b0e; }
    .player-name { font-weight: 600; font-size: 0.9rem; }
    .player-indicator {
      margin-left: auto;
      font-size: 0.75rem;
      color: #5865f2;
      display: none;
    }
    .player-bar.active .player-indicator { display: block; }

    /* ── Board ── */
    .board-with-labels {
      display: grid;
      grid-template-columns: 18px auto;
      grid-template-rows: auto 18px;
      gap: 4px;
      margin: 0;
    }
    .rank-labels {
      display: flex;
      flex-direction: column;
      justify-content: space-around;
      align-items: center;
      font-size: 0.68rem;
      color: #72767d;
      line-height: 1;
    }
    .file-labels {
      grid-column: 2;
      display: flex;
      justify-content: space-around;
      font-size: 0.68rem;
      color: #72767d;
    }
    .board {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      border: 2px solid #111214;
      border-radius: 4px;
      overflow: hidden;
    }
    .square {
      width: 64px; height: 64px;
      display: flex; align-items: center; justify-content: center;
      font-size: 2.4rem;
      position: relative;
    }
    .square.light { background: #f0d9b5; }
    .square.dark  { background: #b58863; }
    .square.hi-from.light, .square.hi-to.light { background: #cdd16e; }
    .square.hi-from.dark,  .square.hi-to.dark  { background: #aaa23a; }
    .piece { line-height: 1; user-select: none; }
    .piece.white { color: #fff; text-shadow: 0 0 2px #000, 0 1px 3px rgba(0,0,0,0.6); }
    .piece.black { color: #1a1a1a; text-shadow: 0 0 2px rgba(255,255,255,0.3); }

    /* ── Sidebar ── */
    .sidebar {
      flex: 1;
      min-width: 220px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .panel {
      background: #2b2d31;
      border-radius: 12px;
      padding: 16px;
    }
    .panel h2 {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #96989d;
      margin-bottom: 12px;
    }

    /* Status badge */
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.875rem;
      font-weight: 600;
    }
    .status-badge.in-progress { background: #1e3a2c; color: #3ba55d; }
    .status-badge.checkmate   { background: #3a1e1e; color: #ed4245; }
    .status-badge.draw,
    .status-badge.stalemate   { background: #3a331e; color: #faa61a; }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: currentColor;
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.35} }
    .turn-info {
      margin-top: 10px;
      font-size: 0.875rem;
      color: #b9bbbe;
    }
    .turn-info strong { color: #fff; }
    .meta-info {
      margin-top: 6px;
      font-size: 0.72rem;
      color: #72767d;
    }

    /* Refresh bar */
    .refresh-bar {
      height: 3px;
      background: #1a1b1e;
      border-radius: 2px;
      overflow: hidden;
      margin-top: 14px;
    }
    .refresh-progress {
      height: 100%;
      background: #5865f2;
      border-radius: 2px;
      transition: width 0.1s linear;
    }
    .refresh-label {
      font-size: 0.68rem;
      color: #4e5058;
      text-align: right;
      margin-top: 4px;
    }

    /* Move list */
    .move-list {
      display: grid;
      grid-template-columns: 26px 1fr 1fr;
      gap: 1px 6px;
      font-size: 0.82rem;
      font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
      max-height: 340px;
      overflow-y: auto;
    }
    .move-list::-webkit-scrollbar { width: 4px; }
    .move-list::-webkit-scrollbar-track { background: transparent; }
    .move-list::-webkit-scrollbar-thumb { background: #4e5058; border-radius: 2px; }
    .move-num  { color: #4e5058; padding: 2px 0; }
    .move-white { color: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
    .move-black { color: #a0a0a0; padding: 2px 5px; border-radius: 3px; }
    .move-white.latest, .move-black.latest {
      background: #5865f2;
      color: #fff;
    }

    .placeholder { color: #4e5058; font-style: italic; font-size: 0.82rem; }

    /* ── Responsive ── */
    @media (max-width: 680px) {
      .game-container { flex-direction: column; align-items: center; }
      .square { width: 42px; height: 42px; font-size: 1.6rem; }
      .sidebar { width: 100%; max-width: 360px; }
      .move-list { max-height: 240px; }
    }
    @media (max-width: 390px) {
      .square { width: 36px; height: 36px; font-size: 1.3rem; }
    }
  </style>
</head>
<body>
  <header>
    <h1>♟ Jarvis vs Gromozeka</h1>
    <p class="subtitle">Bot-vs-bot chess · live updates every 3s</p>
  </header>

  <div class="game-container">
    <!-- Board column -->
    <div class="board-section">
      <div class="player-bar" id="bar-black">
        <div class="player-avatar black">🤖</div>
        <span class="player-name">Gromozeka (Black)</span>
        <span class="player-indicator">● thinking…</span>
      </div>

      <div class="board-with-labels">
        <div class="rank-labels">
          <span>8</span><span>7</span><span>6</span><span>5</span>
          <span>4</span><span>3</span><span>2</span><span>1</span>
        </div>
        <div class="board" id="board"></div>
        <div></div>
        <div class="file-labels">
          <span>a</span><span>b</span><span>c</span><span>d</span>
          <span>e</span><span>f</span><span>g</span><span>h</span>
        </div>
      </div>

      <div class="player-bar bottom" id="bar-white">
        <div class="player-avatar white">🤖</div>
        <span class="player-name">Jarvis (White)</span>
        <span class="player-indicator">● thinking…</span>
      </div>
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      <div class="panel">
        <h2>Game Status</h2>
        <div id="status-content"><span class="placeholder">Loading…</span></div>
        <div class="refresh-bar">
          <div class="refresh-progress" id="refresh-progress" style="width:100%"></div>
        </div>
        <div class="refresh-label" id="refresh-label">connecting…</div>
      </div>

      <div class="panel">
        <h2>Move List</h2>
        <div class="move-list" id="move-list">
          <span class="placeholder" style="grid-column:1/-1">Loading…</span>
        </div>
      </div>
    </div>
  </div>

<script>
  const GAME_ID   = '115654c4-e476-4f9d-b3f3-892af530aa8c';
  const API_BASE  = 'https://chess-api-lbelyaevs-projects.vercel.app';
  const REFRESH   = 3000;

  const PIECES = {
    K:'♔', Q:'♕', R:'♖', B:'♗', N:'♘', P:'♙',
    k:'♚', q:'♛', r:'♜', b:'♝', n:'♞', p:'♟'
  };

  // ── FEN → 8×8 array (row 0 = rank 8) ──────────────────────────────
  function parseFen(fen) {
    return fen.split(' ')[0].split('/').map(row => {
      const rank = [];
      for (const ch of row) {
        const n = parseInt(ch);
        if (!isNaN(n)) for (let i = 0; i < n; i++) rank.push(null);
        else rank.push(ch);
      }
      return rank;
    });
  }

  // UCI "e2e4" → { fr, ff, tr, tf }
  function uciSquares(uci) {
    if (!uci || uci.length < 4) return null;
    return {
      ff: uci.charCodeAt(0) - 97,
      fr: 8 - parseInt(uci[1]),
      tf: uci.charCodeAt(2) - 97,
      tr: 8 - parseInt(uci[3])
    };
  }

  // "e2e4" → "e2→e4"
  function fmtMove(uci) {
    return uci ? uci.slice(0,2) + '→' + uci.slice(2,4) : '';
  }

  // ── Render board ───────────────────────────────────────────────────
  function renderBoard(fen, lastMove) {
    const grid  = parseFen(fen);
    const hi    = lastMove ? uciSquares(lastMove) : null;
    const board = document.getElementById('board');
    board.innerHTML = '';

    for (let r = 0; r < 8; r++) {
      for (let f = 0; f < 8; f++) {
        const sq = document.createElement('div');
        const light = (r + f) % 2 === 0;
        sq.className = 'square ' + (light ? 'light' : 'dark');
        if (hi) {
          if (r === hi.fr && f === hi.ff) sq.classList.add('hi-from');
          if (r === hi.tr && f === hi.tf) sq.classList.add('hi-to');
        }
        const piece = grid[r][f];
        if (piece) {
          const sp = document.createElement('span');
          sp.className = 'piece ' + (piece === piece.toUpperCase() ? 'white' : 'black');
          sp.textContent = PIECES[piece] || piece;
          sq.appendChild(sp);
        }
        board.appendChild(sq);
      }
    }
  }

  // ── Render move list ───────────────────────────────────────────────
  function renderMoves(moves) {
    const el = document.getElementById('move-list');
    if (!moves || moves.length === 0) {
      el.innerHTML = '<span class="placeholder" style="grid-column:1/-1">No moves yet</span>';
      return;
    }
    el.innerHTML = '';
    const pairs = Math.ceil(moves.length / 2);
    for (let i = 0; i < pairs; i++) {
      const wi = i * 2, bi = i * 2 + 1;
      const isLastW = wi === moves.length - 1;
      const isLastB = bi === moves.length - 1;

      const num = document.createElement('span');
      num.className = 'move-num';
      num.textContent = (i + 1) + '.';

      const w = document.createElement('span');
      w.className = 'move-white' + (isLastW ? ' latest' : '');
      w.textContent = fmtMove(moves[wi]);

      const b = document.createElement('span');
      b.className = 'move-black' + (isLastB ? ' latest' : '');
      b.textContent = moves[bi] ? fmtMove(moves[bi]) : '';

      el.appendChild(num);
      el.appendChild(w);
      el.appendChild(b);
    }
    el.scrollTop = el.scrollHeight;
  }

  // ── Time helper ────────────────────────────────────────────────────
  function timeAgo(iso) {
    if (!iso) return 'unknown';
    const secs = Math.floor((Date.now() - new Date(iso.endsWith('Z') ? iso : iso + 'Z')) / 1000);
    if (secs <  5)    return 'just now';
    if (secs < 60)    return secs + 's ago';
    if (secs < 3600)  return Math.floor(secs / 60) + 'm ago';
    return Math.floor(secs / 3600) + 'h ago';
  }

  // ── Render status ──────────────────────────────────────────────────
  function renderStatus(data) {
    const st = data.status || 'unknown';
    const cls = { in_progress:'in-progress', checkmate:'checkmate', draw:'draw', stalemate:'stalemate' }[st] || 'in-progress';
    const label = { in_progress:'In Progress', checkmate:'Checkmate', draw:'Draw', stalemate:'Stalemate' }[st] || st;
    const dot   = st === 'in_progress' ? '<div class="dot"></div>' : '';
    const turnText = st === 'in_progress'
      ? `<strong>${data.current_player}</strong> to move`
      : `Game over — ${label}`;

    document.getElementById('status-content').innerHTML = `
      <div class="status-badge ${cls}">${dot}${label}</div>
      <div class="turn-info">${turnText}</div>
      <div class="meta-info">Move ${(data.moves||[]).length} · Updated ${timeAgo(data.updated_at)}</div>
    `;

    document.getElementById('bar-white').classList.toggle('active',
      st === 'in_progress' && data.current_player === data.white);
    document.getElementById('bar-black').classList.toggle('active',
      st === 'in_progress' && data.current_player === data.black);
  }

  // ── Fetch & render ─────────────────────────────────────────────────
  async function fetchAndRender() {
    try {
      const res  = await fetch(`${API_BASE}/game/${GAME_ID}`);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const last = data.moves?.length ? data.moves[data.moves.length - 1] : null;
      renderBoard(data.fen, last);
      renderMoves(data.moves);
      renderStatus(data);
    } catch (e) {
      document.getElementById('status-content').innerHTML =
        `<span style="color:#ed4245;font-size:.85rem">⚠ ${e.message}</span>`;
    }
  }

  // ── Countdown progress bar ─────────────────────────────────────────
  let nextAt = Date.now() + REFRESH;
  setInterval(() => {
    const rem = Math.max(0, nextAt - Date.now());
    document.getElementById('refresh-progress').style.width = (rem / REFRESH * 100) + '%';
    document.getElementById('refresh-label').textContent =
      `next refresh in ${(rem / 1000).toFixed(1)}s`;
  }, 100);

  // ── Main loop ──────────────────────────────────────────────────────
  (async function loop() {
    await fetchAndRender();
    nextAt = Date.now() + REFRESH;
    setTimeout(loop, REFRESH);
  })();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    """Chess viewer web UI"""
    return CHESS_VIEWER_HTML


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