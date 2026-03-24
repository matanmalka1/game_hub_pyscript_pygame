import math, random
import numpy as np

# ── Constants ────────────────────────────────────────────────────────────
WIN_COMBOS = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
LEVEL_NOISE = {"rookie":0.9,"easy":0.65,"even":0.35,"hard":0.15,"expert":0.0}

# ── Neural Network ───────────────────────────────────────────────────────
def relu(x):
    return np.maximum(0, x)

def softmax(x):
    e = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e / np.sum(e, axis=1, keepdims=True)

class TicTacToeNN:
    def __init__(self, hidden=64):
        scale = 0.1
        self.W1 = np.random.randn(9, hidden) * scale
        self.b1 = np.zeros((1, hidden))
        self.W2 = np.random.randn(hidden, 9) * scale
        self.b2 = np.zeros((1, 9))

    def predict(self, x):
        A1 = relu(x @ self.W1 + self.b1)
        return softmax(A1 @ self.W2 + self.b2)[0]

    def forward(self, x):
        A1 = relu(x @ self.W1 + self.b1)
        return softmax(A1 @ self.W2 + self.b2)

    def save_weights(self):
        return {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2}

    def load_weights(self, d):
        self.W1, self.b1, self.W2, self.b2 = d["W1"], d["b1"], d["W2"], d["b2"]

# ── Minimax ──────────────────────────────────────────────────────────────
def check_win_flat(b, p):
    for a, bb, c in WIN_COMBOS:
        if b[a] == b[bb] == b[c] == p: return True
    return False

def minimax(b, is_max, alpha=-math.inf, beta=math.inf, depth=0):
    if check_win_flat(b, 1):  return 10 - depth
    if check_win_flat(b, -1): return depth - 10
    if 0 not in b:            return 0
    if is_max:
        best = -math.inf
        for i in range(9):
            if b[i] == 0:
                b[i] = 1; best = max(best, minimax(b, False, alpha, beta, depth+1)); b[i] = 0
                alpha = max(alpha, best)
                if beta <= alpha: break
        return best
    else:
        best = math.inf
        for i in range(9):
            if b[i] == 0:
                b[i] = -1; best = min(best, minimax(b, True, alpha, beta, depth+1)); b[i] = 0
                beta = min(beta, best)
                if beta <= alpha: break
        return best

def best_minimax_move(b, player):
    empty = [i for i in range(9) if b[i] == 0]
    if not empty: return -1
    best_val = -math.inf if player == 1 else math.inf
    best_mv  = empty[0]
    for i in empty:
        b[i] = player
        val = minimax(b, player == -1, depth=0)
        b[i] = 0
        if (player == 1 and val > best_val) or (player == -1 and val < best_val):
            best_val, best_mv = val, i
    return best_mv

# ── Self-play data generation ────────────────────────────────────────────
def generate_game(noise):
    b = [0] * 9
    states, labels = [], []
    player = 1
    while True:
        empty = [i for i in range(9) if b[i] == 0]
        if not empty: break
        flat = np.array([1 if b[i]==player else (-1 if b[i]==-player else 0) for i in range(9)], dtype=float)
        mv = random.choice(empty) if random.random() < noise else best_minimax_move(b[:], player)
        probs = np.zeros(9); probs[mv] = 1.0
        states.append(flat); labels.append(probs)
        b[mv] = player
        if check_win_flat(b, player): break
        player = -player
    return states, labels

def generate_dataset(noise, n_games=300):
    X, Y = [], []
    for _ in range(n_games):
        s, l = generate_game(noise)
        X.extend(s); Y.extend(l)
    return np.array(X), np.array(Y)

# ── Training step ────────────────────────────────────────────────────────
def cross_entropy_loss(pred, target):
    return -np.mean(np.sum(target * np.log(pred + 1e-9), axis=1))

def train_step(model, X, Y, lr=0.005):
    A1 = relu(X @ model.W1 + model.b1)
    Z2 = A1 @ model.W2 + model.b2
    e  = np.exp(Z2 - np.max(Z2, axis=1, keepdims=True))
    A2 = e / np.sum(e, axis=1, keepdims=True)
    loss = cross_entropy_loss(A2, Y)
    dZ2 = (A2 - Y) / len(X)
    dW2 = A1.T @ dZ2
    db2 = np.sum(dZ2, axis=0, keepdims=True)
    dA1 = dZ2 @ model.W2.T
    dZ1 = dA1 * (A1 > 0)
    dW1 = X.T @ dZ1
    db1 = np.sum(dZ1, axis=0, keepdims=True)
    model.W1 -= lr * dW1; model.b1 -= lr * db1
    model.W2 -= lr * dW2; model.b2 -= lr * db2
    return loss

# ── Shared model registry ────────────────────────────────────────────────
trained_models = {}
for lvl in ["rookie", "easy", "even", "hard", "expert"]:
    trained_models[lvl] = TicTacToeNN(hidden=64)

# ── Game logic ───────────────────────────────────────────────────────────
def check_win(board, player):
    for c in range(3):
        if board[0][c] == board[1][c] == board[2][c] == player: return True
    for r in range(3):
        if board[r][0] == board[r][1] == board[r][2] == player: return True
    return (board[0][0] == board[1][1] == board[2][2] == player or
            board[0][2] == board[1][1] == board[2][0] == player)

def is_draw(board):
    return all(board[r][c] != 0 for r in range(3) for c in range(3))

def get_ai_move(board, model, ai_player):
    human = 3 - ai_player
    flat = np.array([
        1 if board[r][c]==ai_player else (-1 if board[r][c]==human else 0)
        for r in range(3) for c in range(3)
    ], dtype=float).reshape(1, -1)
    probs = model.predict(flat)
    for r in range(3):
        for c in range(3):
            if board[r][c] != 0: probs[r*3+c] = 0.0
    total = probs.sum()
    if total == 0:
        empty = [(r,c) for r in range(3) for c in range(3) if board[r][c] == 0]
        return random.choice(empty) if empty else None
    probs /= total
    idx = np.random.choice(9, p=probs)
    return divmod(idx, 3)
