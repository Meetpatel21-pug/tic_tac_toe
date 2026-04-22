from flask import Flask, render_template, redirect, url_for, request
import sqlite3
import uuid
import random

app = Flask(__name__)

# --- Database helpers ---
def get_db():
    conn = sqlite3.connect("tic.db")
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
            game_mode TEXT DEFAULT 'friend'
        )
    """)
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
        return list(game["board"]), game["current_player"], game["x_wins"], game["o_wins"], game["draws"], game_mode
    return None, None, None, None, None, None

def create_game(game_id, game_mode="friend"):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO game (id, board, current_player, x_wins, o_wins, draws, game_mode) VALUES (?, ?, ?, 0, 0, 0, ?)",
                 (game_id, "-"*9, "X", game_mode))
    conn.commit()
    conn.close()

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
        game_id = request.form["game_id"]
        if game_id:  # Only join existing game if ID provided
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
    board, current_player, x_wins, o_wins, draws, game_mode = get_game(game_id)
    if board is None:
        return f"Game {game_id} not found. Please create a new game."
    winner = check_winner(board)
    if winner:
        update_score(game_id, winner)
    elif "-" not in board and not winner:
        update_score(game_id, "Draw")
    return render_template("index.html", board=board, current=current_player, winner=winner,
                           game_id=game_id, x_wins=x_wins, o_wins=o_wins, draws=draws, game_mode=game_mode)

@app.route("/move/<game_id>/<int:cell>")
def move(game_id, cell):
    board, current_player, _, _, _, game_mode = get_game(game_id)
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
    return redirect(url_for("index", game_id=game_id))

@app.route("/reset/<game_id>")
def reset(game_id):
    # Reset board but keep scores
    conn = get_db()
    conn.execute("UPDATE game SET board=?, current_player=? WHERE id=?", ("-"*9, "X", game_id))
    conn.commit()
    conn.close()
    return redirect(url_for("index", game_id=game_id))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
