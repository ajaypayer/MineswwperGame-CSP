from flask import Flask, render_template, request, jsonify
import random
import json
import traceback

app = Flask(__name__)

# Game configurations
DIFFICULTIES = {
    'easy': {'rows': 5, 'cols': 5, 'mines': 5},
    'medium': {'rows': 7, 'cols': 7, 'mines': 10},
    'hard': {'rows': 8, 'cols': 8, 'mines': 15}
}

class MinesweeperGame:
    def __init__(self, rows, cols, mines):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.board = [[0 for _ in range(cols)] for _ in range(rows)]
        self.revealed = [[False for _ in range(cols)] for _ in range(rows)]
        self.flagged = [[False for _ in range(cols)] for _ in range(rows)]
        self.game_over = False
        self.won = False
        self.mine_positions = []
        self.place_mines()
        self.calculate_numbers()

    def place_mines(self):
        positions = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.mine_positions = random.sample(positions, self.mines)
        for i, j in self.mine_positions:
            self.board[i][j] = 9

    def calculate_numbers(self):
        for i in range(self.rows):
            for j in range(self.cols):
                if self.board[i][j] != 9:
                    count = 0
                    for ni, nj in self.get_neighbors(i, j):
                        if self.board[ni][nj] == 9: count += 1
                    self.board[i][j] = count

    def get_neighbors(self, i, j):
        return [(i+di, j+dj) for di in [-1,0,1] for dj in [-1,0,1] 
                if (di!=0 or dj!=0) and 0<=i+di<self.rows and 0<=j+dj<self.cols]

    def reveal(self, i, j):
        if self.revealed[i][j] or self.flagged[i][j] or self.game_over:
            return False, False
        self.revealed[i][j] = True
        if self.board[i][j] == 9:
            self.game_over = True
            return True, False
        if self.board[i][j] == 0:
            for ni, nj in self.get_neighbors(i, j):
                if not self.revealed[ni][nj]: self.reveal(ni, nj)
        self.check_win()
        return False, self.won

    def flag(self, i, j):
        if self.revealed[i][j] or self.game_over: return
        self.flagged[i][j] = not self.flagged[i][j]
        self.check_win()

    def check_win(self):
        revealed_count = sum(sum(row) for row in self.revealed)
        if revealed_count == self.rows * self.cols - self.mines:
            self.won, self.game_over = True, True
            return
        mine_set = set(self.mine_positions)
        flag__positions = [(i, j) for i in range(self.rows) for j in range(self.cols) if self.flagged[i][j]]
        if set(flag__positions) == mine_set:
            self.won, self.game_over = True, True

    def get_state(self):
        state = []
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                if self.flagged[i][j]: row.append('F')
                elif self.revealed[i][j]: row.append('M' if self.board[i][j] == 9 else str(self.board[i][j]))
                else: row.append('?')
            state.append(row)
        return state

class MinesweeperAI:
    def __init__(self, game):
        self.game = game
        self.steps = []
        self.branching_graph = {'frontier': None, 'candidates': [], 'deduction': None}

    def get_neighbors(self, i, j):
        return self.game.get_neighbors(i, j)

    def get_local_fragment(self, pivot_vars):
        if not pivot_vars: return [], 0, 0
        p_list = list(pivot_vars)
        min_i, max_i = min(v[0] for v in p_list), max(v[0] for v in p_list)
        min_j, max_j = min(v[1] for v in p_list), max(v[1] for v in p_list)
        min_i, max_i = max(0, min_i-1), min(self.game.rows-1, max_i+1)
        min_j, max_j = max(0, min_j-1), min(self.game.cols-1, max_j+1)
        state = self.game.get_state()
        fragment = [state[i][min_j:max_j+1] for i in range(min_i, max_i+1)]
        return fragment, min_i, min_j

    def solve_csp(self):
        total_mines_left = self.game.mines - sum(sum(row) for row in self.game.flagged)
        all_unknowns = [(r, c) for r in range(self.game.rows) for c in range(self.game.cols) 
                        if not self.game.revealed[r][c] and not self.game.flagged[r][c]]
        if not all_unknowns: return None, None

        all_vars, all_constraints = set(), []
        for i in range(self.game.rows):
            for j in range(self.game.cols):
                if self.game.revealed[i][j] and self.game.board[i][j] > 0:
                    neighs = self.get_neighbors(i, j)
                    unrev = [n for n in neighs if not self.game.revealed[n[0]][n[1]]]
                    unknowns = [n for n in unrev if not self.game.flagged[n[0]][n[1]]]
                    flagged = [n for n in unrev if self.game.flagged[n[0]][n[1]]]
                    if unknowns:
                        needed = self.game.board[i][j] - len(flagged)
                        all_constraints.append({'vars': set(unknowns), 'count': needed})
                        all_vars.update(unknowns)

        # Fast Logic Stage
        for c in all_constraints:
            if c['count'] == 0:
                v = list(c['vars'])[0]
                self.steps.append(f"Logic: {v} is SAFE")
                self.record_graph(list(c['vars']), [], v, 'reveal')
                return 'reveal', v
            if c['count'] == len(c['vars']):
                v = list(c['vars'])[0]
                self.steps.append(f"Logic: {v} is MINE")
                self.record_graph(list(c['vars']), [], v, 'flag')
                return 'flag', v

        # Partitioning
        clusters, visited = [], set()
        var_to_const = {v: [] for v in all_vars}
        for c in all_constraints:
            for v in c['vars']: var_to_const[v].append(c)
        for v in all_vars:
            if v not in visited:
                cv, cc, q = set(), set(), [v]
                visited.add(v)
                while q:
                    cur = q.pop(0); cv.add(cur)
                    for const in var_to_const[cur]:
                        cc.add(id(const))
                        for nv in const['vars']:
                            if nv not in visited: visited.add(nv); q.append(nv)
                clusters.append({'vars': list(cv), 'constraints': [c for c in all_constraints if id(c) in cc]})

        final_probs = {}
        for cluster in clusters:
            v_list = cluster['vars']
            if len(v_list) > 100: v_list = v_list[:100]
            solutions = []
            def backtrack(idx, current):
                if idx == len(v_list):
                    for c in cluster['constraints']:
                        if sum(current.get(v, 0) for v in c['vars'] if v in current) != c['count']: return
                    solutions.append(current.copy()); return
                for val in [0, 1]:
                    current[v_list[idx]] = val
                    ok = True
                    for c in cluster['constraints']:
                        assigned = [v for v in c['vars'] if v in current]
                        ac, rem = sum(current[v] for v in assigned), len(c['vars']) - len(assigned)
                        if ac > c['count'] or ac + rem < c['count']: ok = False; break
                    if ok and sum(current.values()) <= total_mines_left: backtrack(idx + 1, current)
                    del current[v_list[idx]]
            backtrack(0, {})
            if not solutions: continue
            counts = {v: 0 for v in v_list}
            for sol in solutions:
                for v, val in sol.items():
                    if val == 1: counts[v] += 1
            for v in v_list:
                p = counts[v] / len(solutions)
                final_probs[v] = {'p': p, 'solutions': solutions, 'vars': v_list}
                if p == 0:
                    self.steps.append(f"CSP Deducted: {v} is SAFE")
                    self.record_graph(v_list, solutions, v, 'reveal')
                    return 'reveal', v
                if p == 1:
                    self.steps.append(f"CSP Deducted: {v} is MINE")
                    self.record_graph(v_list, solutions, v, 'flag')
                    return 'flag', v

        # Global Probability
        frontier_vars = set(final_probs.keys())
        non_frontier = [v for v in all_unknowns if v not in frontier_vars]
        if non_frontier:
            p_global = total_mines_left / len(all_unknowns)
            for v in non_frontier: final_probs[v] = {'p': p_global, 'solutions': [], 'vars': [v]}

        # Decision
        if final_probs:
            best_v = min(final_probs.keys(), key=lambda v: final_probs[v]['p'])
            self.steps.append(f"Minimum Risk: {best_v} ({final_probs[best_v]['p']*100:.1f}%)")
            self.record_graph(final_probs[best_v]['vars'], final_probs[best_v]['solutions'], best_v, 'reveal')
            return 'reveal', best_v

        if all_unknowns:
            v = random.choice(all_unknowns)
            self.steps.append(f"Fallback: {v}")
            self.record_graph([v], [], v, 'reveal')
            return 'reveal', v
        return None, None

    def record_graph(self, vars, sols, target, action):
        fragment, f_mi, f_mj = self.get_local_fragment(vars)
        self.branching_graph['frontier'] = {'label': 'Frontier', 'grid': fragment}
        for idx, s in enumerate(sols[:4]):
            c_grid = [row[:] for row in fragment]
            for cv, val in s.items():
                li, lj = cv[0]-f_mi, cv[1]-f_mj
                if 0<=li<len(c_grid) and 0<=lj<len(c_grid[0]): c_grid[li][lj] = 'M_HYP' if val==1 else 'S_HYP'
            self.branching_graph['candidates'].append({'label': f'Hypothesis {idx+1}', 'grid': c_grid})
        dec_grid = [row[:] for row in fragment]
        li, lj = target[0]-f_mi, target[1]-f_mj
        if 0<=li<len(dec_grid) and 0<=lj<len(dec_grid[0]): dec_grid[li][lj] = '✅' if action=='reveal' else '🚩'
        self.branching_graph['deduction'] = {'label': f'Decision: {target}', 'grid': dec_grid}

    def find_move(self):
        revealed_any = any(any(row) for row in self.game.revealed)
        if not revealed_any:
            safe_opening_cells = [(self.game.rows//2, self.game.cols//2), (self.game.rows//2 - 1, self.game.cols//2),
                                  (self.game.rows//2, self.game.cols//2 - 1), (self.game.rows//2 - 1, self.game.cols//2 - 1)]
            cell = random.choice(safe_opening_cells)
            self.steps.append(f"Safe Opening: {cell}")
            self.record_graph([cell], [], cell, 'reveal')
            return 'reveal', cell
        return self.solve_csp()

games = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/user')
def user():
    difficulty = request.args.get('difficulty', 'easy')
    return render_template('user.html', difficulty=difficulty)

@app.route('/ai')
def ai():
    difficulty = request.args.get('difficulty', 'easy')
    return render_template('ai.html', difficulty=difficulty)

@app.route('/api/new_game', methods=['POST'])
def new_game():
    data = request.json
    diff = data.get('difficulty', 'easy')
    conf = DIFFICULTIES.get(diff, DIFFICULTIES['easy'])
    game = MinesweeperGame(conf['rows'], conf['cols'], conf['mines'])
    game_id = str(random.randint(1000, 9999))
    games[game_id] = game
    return jsonify({'game_id': game_id, 'state': game.get_state(), 'game_over': False, 'won': False})

@app.route('/api/reveal', methods=['POST'])
def reveal():
    data = request.json
    game_id = data['game_id']
    game = games.get(game_id)
    if not game: return jsonify({'error': 'Invalid Game'}), 400
    hit_mine, won = game.reveal(data['i'], data['j'])
    return jsonify({'state': game.get_state(), 'game_over': game.game_over, 'won': won})

@app.route('/api/flag', methods=['POST'])
def flag():
    data = request.json
    game_id = data['game_id']
    game = games.get(game_id)
    if not game: return jsonify({'error': 'Invalid Game'}), 400
    game.flag(data['i'], data['j'])
    return jsonify({'state': game.get_state(), 'game_over': game.game_over, 'won': game.won})

@app.route('/api/ai_move', methods=['POST'])
def ai_move():
    game_id = request.json.get('game_id')
    game = games.get(game_id)
    if not game: return jsonify({'error': 'Invalid Game'}), 400
    action, cell, steps, graph_data = None, None, [], {}
    try:
        ai = MinesweeperAI(game)
        action, cell = ai.find_move()
        if action == 'reveal': game.reveal(cell[0], cell[1])
        elif action == 'flag': game.flag(cell[0], cell[1])
        steps, graph_data = ai.steps, ai.branching_graph
    except Exception:
        print(f"CRASH: {traceback.format_exc()}")
        unknowns = [(r, c) for r in range(game.rows) for c in range(game.cols) if not game.revealed[r][c] and not game.flagged[r][c]]
        if unknowns:
            cell = random.choice(unknowns); action = 'reveal'
            game.reveal(cell[0], cell[1])
            steps = ["Safety Fallback Used"]
    return jsonify({'action': action, 'cell': cell, 'state': game.get_state(), 'game_over': game.game_over, 'won': game.won, 'graph_steps': steps, 'branching_graph': graph_data})

if __name__ == '__main__':
    app.run(debug=True)