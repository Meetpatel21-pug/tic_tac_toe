from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import sqlite3
import uuid
import random
import os
import traceback
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "tic-tac-toe-secret")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tic.db")


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    return traceback.format_exc(), 500, {"Content-Type": "text/plain; charset=utf-8"}
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# --- Database helpers ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS game (
            id TEXT PRIMARY KEY,
            board TEXT,
            current_player TEXT,
            x_wins INTEGER DEFAULT 0,
            o_wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            game_mode TEXT DEFAULT 'friend',
            result_recorded INTEGER DEFAULT 0,
            x_player_id TEXT,
            o_player_id TEXT
        )
    """)

    # Backward-compatible migration for existing databases.
    cols = [row[1] for row in c.execute("PRAGMA table_info(game)").fetchall()]
    if "game_mode" not in cols:
        c.execute("ALTER TABLE game ADD COLUMN game_mode TEXT DEFAULT 'friend'")
    if "result_recorded" not in cols:
        c.execute("ALTER TABLE game ADD COLUMN result_recorded INTEGER DEFAULT 0")
    if "x_player_id" not in cols:
        c.execute("ALTER TABLE game ADD COLUMN x_player_id TEXT")
    if "o_player_id" not in cols:
        c.execute("ALTER TABLE game ADD COLUMN o_player_id TEXT")

    conn.commit()
    conn.close()

def get_game(game_id):
    conn = get_db()
    game = conn.execute("SELECT * FROM game WHERE id=?", (game_id,)).fetchone()
    conn.close()
    if game:
        try:
            game_mode = game["game_mode"]
        except (IndexError, KeyError):
            game_mode = "friend"
        result_recorded = game["result_recorded"] if "result_recorded" in game.keys() else 0
        x_player_id = game["x_player_id"] if "x_player_id" in game.keys() else None
        o_player_id = game["o_player_id"] if "o_player_id" in game.keys() else None
        return list(game["board"]), game["current_player"], game["x_wins"], game["o_wins"], game["draws"], game_mode, result_recorded, x_player_id, o_player_id
    return None, None, None, None, None, None, None, None, None

def create_game(game_id, game_mode="friend"):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO game (id, board, current_player, x_wins, o_wins, draws, game_mode, result_recorded, x_player_id, o_player_id) VALUES (?, ?, ?, 0, 0, 0, ?, 0, NULL, NULL)",
                 (game_id, "-"*9, "X", game_mode))
    conn.commit()
    conn.close()

# Ensure DB/table exist in WSGI environments (PythonAnywhere imports module; __main__ does not run).
init_db()

def update_game(game_id, board, current_player):
    conn = get_db()
    conn.execute("UPDATE game SET board=?, current_player=? WHERE id=?", ("".join(board), current_player, game_id))
    conn.commit()
    conn.close()

def update_score(game_id, winner=None):
    conn = get_db()
    if winner == "X":
        conn.execute("UPDATE game SET x_wins = x_wins + 1 WHERE id=?", (game_id,))
    elif winner == "O":
        conn.execute("UPDATE game SET o_wins = o_wins + 1 WHERE id=?", (game_id,))
    elif winner == "Draw":
        conn.execute("UPDATE game SET draws = draws + 1 WHERE id=?", (game_id,))
    conn.commit()
    conn.close()


def get_or_create_session_player_id():
    player_id = session.get("player_id")
    if not player_id:
        player_id = str(uuid.uuid4())
        session["player_id"] = player_id
    return player_id


def assign_or_get_player_symbol(game_id, game_mode, x_player_id, o_player_id):
    if game_mode != "friend":
        return "X"

    player_id = get_or_create_session_player_id()

    if x_player_id == player_id:
        return "X"
    if o_player_id == player_id:
        return "O"

    if x_player_id and o_player_id:
        return None

    conn = get_db()
    if not x_player_id:
        conn.execute("UPDATE game SET x_player_id=? WHERE id=?", (player_id, game_id))
        conn.commit()
        conn.close()
        return "X"

    if not o_player_id:
        conn.execute("UPDATE game SET o_player_id=? WHERE id=?", (player_id, game_id))
        conn.commit()
        conn.close()
        return "O"

    conn.close()
    return None


def maybe_record_result(game_id, board):
    winner = check_winner(board)
    result = None
    if winner:
        result = winner
    elif "-" not in board:
        result = "Draw"

    if not result:
        return

    conn = get_db()
    row = conn.execute("SELECT result_recorded FROM game WHERE id=?", (game_id,)).fetchone()
    if row and row["result_recorded"]:
        conn.close()
        return

    if result == "X":
        conn.execute("UPDATE game SET x_wins=x_wins+1, result_recorded=1 WHERE id=?", (game_id,))
    elif result == "O":
        conn.execute("UPDATE game SET o_wins=o_wins+1, result_recorded=1 WHERE id=?", (game_id,))
    else:
        conn.execute("UPDATE game SET draws=draws+1, result_recorded=1 WHERE id=?", (game_id,))

    conn.commit()
    conn.close()


def get_join_status_message(game_mode, viewer_symbol, x_player_id, o_player_id):
    if game_mode != "friend":
        return "You are Player X."

    if viewer_symbol == "X":
        if o_player_id:
            return "Player O joined."
        return "Waiting for another player to join."

    if viewer_symbol == "O":
        return "You joined as Player O."

    return "Room is full."

# --- Game logic ---
def check_winner(board):
    wins = [(0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] and board[a] != "-":
            return board[a]
    return None

def get_empty_cells(board):
    return [i for i in range(9) if board[i] == "-"]

def can_win(board, player):
    """Check if player can win in the next move"""
    for cell in get_empty_cells(board):
        test_board = board[:]
        test_board[cell] = player
        if check_winner(test_board) == player:
            return cell
    return None

def get_best_move(board):
    """AI logic for computer (O)"""
    empty = get_empty_cells(board)
    
    if not empty:
        return None
    
    # 1. Win if possible
    winning_move = can_win(board, "O")
    if winning_move is not None:
        return winning_move
    
    # 2. Block player from winning
    blocking_move = can_win(board, "X")
    if blocking_move is not None:
        return blocking_move
    
    # 3. Prefer center
    if 4 in empty:
        return 4
    
    # 4. Prefer corners
    corners = [0, 2, 6, 8]
    corner_moves = [c for c in corners if c in empty]
    if corner_moves:
        return random.choice(corner_moves)
    
    # 5. Take any available move
    return random.choice(empty)

def new_game_id():
    return str(uuid.uuid4())[:8]  # short unique ID

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        game_id = request.form["game_id"].strip()
        if game_id:  # Join existing game; create only if it does not exist.
            board, _, _, _, _, _, _, _, _ = get_game(game_id)
            if board is None:
                create_game(game_id, "friend")
            return redirect(url_for("index", game_id=game_id))
    return render_template("home.html")

@app.route("/new")
def new_game():
    mode = request.args.get("mode", "friend")
    game_id = new_game_id()
    create_game(game_id, mode)
    return redirect(url_for("index", game_id=game_id))

@app.route("/game/<game_id>")
def index(game_id):
    board, current_player, x_wins, o_wins, draws, game_mode, _, x_player_id, o_player_id = get_game(game_id)
    if board is None:
        return f"Game {game_id} not found. Please create a new game."

    viewer_symbol = assign_or_get_player_symbol(game_id, game_mode, x_player_id, o_player_id)
    if game_mode == "friend" and viewer_symbol is None:
        return render_template("home.html", room_full=True, room_id=game_id)

    winner = check_winner(board)
    draw = ("-" not in board and not winner)
    can_move = not winner and not draw and (
        (game_mode == "friend" and viewer_symbol in ["X", "O"] and viewer_symbol == current_player) or
        (game_mode == "computer" and current_player == "X")
    )

    return render_template("index.html", board=board, current=current_player, winner=winner,
                           game_id=game_id, x_wins=x_wins, o_wins=o_wins, draws=draws, game_mode=game_mode,
                           can_move=can_move, viewer_symbol=viewer_symbol,
                           join_status=get_join_status_message(game_mode, viewer_symbol, x_player_id, o_player_id))


@app.route("/state/<game_id>")
def game_state(game_id):
    board, current_player, x_wins, o_wins, draws, game_mode, _, _, _ = get_game(game_id)
    if board is None:
        return jsonify({"error": "not_found"}), 404

    winner = check_winner(board)
    if not winner and "-" not in board:
        winner = "Draw"

    state = {
        "board": "".join(board),
        "current": current_player,
        "winner": winner or "",
        "x_wins": x_wins,
        "o_wins": o_wins,
        "draws": draws,
        "mode": game_mode,
    }
    return jsonify(state)

@app.route("/move/<game_id>/<int:cell>")
def move(game_id, cell):
    board, current_player, _, _, _, game_mode, _, x_player_id, o_player_id = get_game(game_id)
    if board is None:
        return redirect(url_for("home"))

    if game_mode == "friend":
        viewer_symbol = assign_or_get_player_symbol(game_id, game_mode, x_player_id, o_player_id)
        if viewer_symbol is None or viewer_symbol != current_player:
            return redirect(url_for("index", game_id=game_id))

    if board and board[cell] == "-" and not check_winner(board):
        board[cell] = current_player
        winner = check_winner(board)
        
        if not winner and "-" in board:
            current_player = "O" if current_player == "X" else "X"
            
            # If playing against computer and it's computer's turn, make computer move
            if game_mode == "computer" and current_player == "O":
                computer_move = get_best_move(board)
                if computer_move is not None:
                    board[computer_move] = "O"
                    winner = check_winner(board)
                    if not winner and "-" in board:
                        current_player = "X"
        
        update_game(game_id, board, current_player)
        maybe_record_result(game_id, board)
    return redirect(url_for("index", game_id=game_id))

@app.route("/reset/<game_id>")
def reset(game_id):
    # Reset board but keep scores
    conn = get_db()
    conn.execute("UPDATE game SET board=?, current_player=?, result_recorded=0 WHERE id=?", ("-"*9, "X", game_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index", game_id=game_id))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
