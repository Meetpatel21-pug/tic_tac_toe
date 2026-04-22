# Tic Tac Toe Game

A modern Flask web application to play Tic Tac Toe with a friend or against the computer AI.

## Features

- 👥 **Play with Friend** - Two-player mode
- 🤖 **Play with Computer** - Play against AI opponent
- 💾 **Score Tracking** - Keep track of wins and draws
- 🎨 **Modern UI** - Beautiful responsive design
- 🔄 **Game History** - Share games with unique IDs

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tic_tac_toe.git
cd tic_tac_toe
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and go to: `http://127.0.0.1:5000`

## Deployment (PythonAnywhere)

1. Create account at https://www.pythonanywhere.com
2. Go to Web tab → Add new web app → Flask → Python 3.10
3. In Files tab, clone this repository
4. Set WSGI file to point to your app.py
5. Install requirements in virtual environment
6. Reload web app
7. Visit `https://yourusername.pythonanywhere.com`

## Game Modes

### vs Friend
- Both players take turns
- Player 1 is X, Player 2 is O
- Share the game ID to play with someone online

### vs Computer
- You play as X (first player)
- Computer plays as O
- Computer uses smart AI strategy (win, block, center)

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite3
- **Frontend**: HTML/CSS
- **Hosting**: PythonAnywhere

## License

MIT
