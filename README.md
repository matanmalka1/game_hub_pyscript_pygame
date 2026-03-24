# NEXUS ARCADE

A collection of classic browser games built with **PyScript** — Python running entirely in the browser via WebAssembly (Pyodide). No server required, no installs, just open an HTML file.

## Games

| Game | File | Description |
|------|------|-------------|
| 🎮 Hub | `nexus_games/index.html` | Game selection hub |
| ❌⭕ Tic-Tac-Toe | `nexus_games/tictactoe.html` | vs AI with trainable neural net |
| 🐍 Snake | `nexus_games/snake.html` | Classic snake |
| 🧱 Breakout | `nexus_games/breakout.html` | Brick breaker |
| 👾 Invaders | `nexus_games/invaders.html` | Space invaders |
| 🧩 Tetris | `nexus_games/tetris.html` | Tetris |
| 🃏 Memory | `nexus_games/memory.html` | Card memory match |
| 🔢 2048 | `nexus_games/game2048.html` | 2048 tile puzzle |

## Running Locally

Since PyScript fetches local `.py` files via `fetch`, you need to serve the files over HTTP (not `file://`).

```bash
# Python built-in server (from the repo root)
cd nexus_games
python -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

## Tic-Tac-Toe — AI Details

The Tic-Tac-Toe game includes an in-browser trainable AI:

- **Model**: small neural network implemented in pure Python + NumPy
- **Training**: runs entirely in the browser via Pyodide — no backend needed
- **Difficulty levels**: Rookie → Easy → Even → Hard → Expert
- **Export**: trained weights can be downloaded as `.npy` files

### Files

| File | Purpose |
|------|---------|
| `tictactoe_core.py` | Game logic, pre-trained model weights, AI move selection |
| `tictactoe_train.py` | In-browser training loop (self-play) |
| `tictactoe.py` | Canvas renderer, game loop, input handling |
| `tictactoe.html` | Entry point, PyScript config |

## Tech Stack

- [PyScript](https://pyscript.net) `2024.1.1` — Python in the browser
- [Pyodide](https://pyodide.org) — CPython compiled to WebAssembly
- [NumPy](https://numpy.org) — via Pyodide's bundled package (no pip install)
- Vanilla HTML/CSS/Canvas — no JS frameworks

## Project Structure

```
tictactoe/
├── nexus_games/
│   ├── index.html          # hub
│   ├── tictactoe.html
│   ├── tictactoe.py
│   ├── tictactoe_core.py
│   ├── tictactoe_train.py
│   ├── snake.html / snake.py
│   ├── breakout.html / breakout.py
│   ├── invaders.html / invaders.py
│   ├── tetris.html / tetris.py
│   ├── memory.html / memory.py
│   └── game2048.html / game2048.py
├── requirements.txt        # reference only (packages load via Pyodide)
├── .gitignore
└── README.md
```

## Notes

- `requirements.txt` is for reference only — packages are loaded at runtime by Pyodide, not installed via pip.
- The `venv/` directory (if present locally) is excluded from version control.
