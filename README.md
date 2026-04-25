# MinesweeperGame-CSP

## Project Overview

This project is a web-based Minesweeper game built with Python Flask for the backend and HTML/CSS/JavaScript for the frontend.

There are two modes:
- **User Mode**: play Minesweeper manually by revealing and flagging cells.
- **AI Mode**: an AI solver uses constraint satisfaction logic to choose the next move and displays the reasoning as a state-space graph.

## What you do in this project

- Build the game logic in `app.py`.
- Use Flask routes to serve the main menu and game pages.
- Store game state on the server in a dictionary keyed by `game_id`.
- Render the Minesweeper board in the browser using JavaScript.
- Call backend APIs from the frontend to reveal cells, place flags, and request AI moves.
- Display AI decision-making using a graph of state fragments and candidate hypotheses.

## Files and responsibilities

- `app.py` — Flask application and game logic.
  - `MinesweeperGame` class: create board, place mines, calculate adjacent numbers, reveal cells, flag cells, and check win conditions.
  - `MinesweeperAI` class: analyze the board with CSP logic, make safe moves, and return state-space graph data.
  - Flask routes:
    - `/` serves `index.html`
    - `/user` serves the manual play page
    - `/ai` serves the AI solver page
    - `/api/new_game` creates a new game
    - `/api/reveal` reveals a cell
    - `/api/flag` toggles a flag
    - `/api/ai_move` requests the AI to make the next move

- `templates/index.html` — main menu with difficulty selection and mode buttons.
- `templates/user.html` — the interactive user game page.
- `templates/ai.html` — the AI solver page with state-space visualization.
- `static/style.css` — styling for the menus, board, and AI visualization.

## How the project works

1. The player selects a difficulty and chooses either User or AI mode.
2. The frontend requests a new game from `/api/new_game`.
3. The server creates a `MinesweeperGame` and returns the initial hidden board state.
4. The browser draws the grid and updates it after every move.
5. In User mode, clicks send `/api/reveal` or `/api/flag`.
6. In AI mode, pressing "Next AI Move" calls `/api/ai_move`.
7. The AI returns both the chosen action and a branching graph showing how it reasoned.

## AI state-space graph

The AI page uses JavaScript to show the solver's state-space graph:
- `graph.frontier`: the current board fragment the AI is focusing on.
- `graph.candidates`: up to four candidate mine/safe hypotheses the AI considered.
- `graph.deduction`: the final decision, marking the chosen cell as safe (`✅`) or mine (`🚩`).

This visualization is created in `templates/ai.html` by the functions:
- `renderBranchingGraph(graph)`
- `createMiniGrid(grid)`
- `updateSteps(steps)`

They render the board fragment and the AI reasoning as small grids beside the main board.

## How to run

1. Install Flask if you do not already have it:
   ```bash
   pip install flask
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open `http://127.0.0.1:5000` in your browser.

## What to improve or add next

- Add a persistent leaderboard or best-time tracking.
- Show the full mine layout when the game ends.
- Improve AI visualization with clearer probability labels.
- Add sound effects or animations for user feedback.
