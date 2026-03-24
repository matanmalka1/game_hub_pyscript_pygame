import asyncio, math
from js import document, window
from pyodide.ffi import create_proxy

from tictactoe_core import (
    trained_models, check_win, is_draw, get_ai_move
)

# ── Canvas ───────────────────────────────────────────────────────────────
canvas = document.getElementById("gameCanvas")
ctx    = canvas.getContext("2d")
W, H   = 360, 460
MARGIN = 24
OFFSET = 110    # top area height
SQ     = (W - MARGIN*2) // 3   # ≈ 104

# Palette
BG_TOP    = "#07090f"
BG_BOT    = "#0d1528"
GRID_COL  = "rgba(255,255,255,0.25)"
CELL_BG   = "rgba(255,255,255,0.08)"
X_COL     = "#ff4d6d"
X_GLOW    = "rgba(255,77,109,0.45)"
O_COL     = "#00e5ff"
O_GLOW    = "rgba(0,229,255,0.45)"
WIN_COL   = "#ffe066"
WIN_GLOW  = "rgba(255,224,102,0.6)"
SPACE     = 26

# ── Voice engine ─────────────────────────────────────────────────────────
_voice_unlocked = False
_speech_queue   = []
_speaking       = False

def _unlock_voice():
    global _voice_unlocked
    if _voice_unlocked: return
    try:
        u = window.SpeechSynthesisUtterance.new("")
        window.speechSynthesis.speak(u)
        _voice_unlocked = True
        document.getElementById("voice-log").textContent = "🔊 Voice enabled"
    except: pass

def _speak_next():
    global _speaking
    if _speaking or not _speech_queue: return
    if not _voice_unlocked: return
    _speaking = True
    text = _speech_queue.pop(0)
    document.getElementById("voice-log").textContent = f"🗣 {text}"
    try:
        u = window.SpeechSynthesisUtterance.new(text)
        u.rate  = 1.0
        u.pitch = 1.1
        def on_end(e):
            global _speaking
            _speaking = False
            _speak_next()
        u.onend   = create_proxy(on_end)
        u.onerror = create_proxy(on_end)
        window.speechSynthesis.speak(u)
    except:
        _speaking = False

def speak(text):
    _speech_queue.append(text)
    _speak_next()

# ── Drawing ──────────────────────────────────────────────────────────────
_tick = 0   # animation counter

def _rrect(x, y, w, h, r):
    ctx.beginPath()
    ctx.moveTo(x + r, y)
    ctx.lineTo(x + w - r, y)
    ctx.arcTo(x + w, y, x + w, y + r, r)
    ctx.lineTo(x + w, y + h - r)
    ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
    ctx.lineTo(x + r, y + h)
    ctx.arcTo(x, y + h, x, y + h - r, r)
    ctx.lineTo(x, y + r)
    ctx.arcTo(x, y, x + r, y, r)
    ctx.closePath()

def _glow(color, blur=18):
    ctx.shadowColor = color
    ctx.shadowBlur  = blur

def _no_glow():
    ctx.shadowColor = "transparent"
    ctx.shadowBlur  = 0

def _find_win_line(b, player):
    """Return (r0,c0,r1,c1) for the winning line, or None."""
    for r in range(3):
        if all(b[r][c]==player for c in range(3)):
            return (r,0,r,2)
    for c in range(3):
        if all(b[r][c]==player for r in range(3)):
            return (0,c,2,c)
    if all(b[i][i]==player for i in range(3)):
        return (0,0,2,2)
    if all(b[i][2-i]==player for i in range(3)):
        return (0,2,2,0)
    return None

def cell_center(r, c):
    cx = MARGIN + c*SQ + SQ//2
    cy = OFFSET + r*SQ + SQ//2
    return cx, cy

def draw():
    global _tick
    _tick += 1

    # ── background gradient ──
    grad = ctx.createLinearGradient(0, 0, 0, H)
    grad.addColorStop(0, BG_TOP)
    grad.addColorStop(1, BG_BOT)
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, W, H)

    # ── header area ──
    board_right = MARGIN + 3*SQ
    board_bot   = OFFSET + 3*SQ

    # subtle top panel separator
    ctx.fillStyle = "rgba(255,255,255,0.03)"
    _rrect(MARGIN-4, 12, board_right - MARGIN + 8, OFFSET - 20, 12)
    ctx.fill()

    # status text
    if game_over:
        if winner == 0:
            msg, col = "DRAW", "#ffe066"
        elif winner == human_player:
            msg, col = "YOU WIN!", "#00e5ff"
        else:
            msg, col = "AI WINS", "#ff4d6d"
    elif current_turn == human_player:
        msg, col = "YOUR TURN", "#00e5ff"
    else:
        # pulsing dots
        dots = "." * ((_tick // 8) % 4)
        msg, col = f"AI THINKING{dots}", "rgba(255,255,255,0.5)"

    ctx.textAlign    = "center"
    ctx.textBaseline = "middle"
    ctx.font         = "bold 20px 'Segoe UI', system-ui, sans-serif"
    _glow(col, 14)
    ctx.fillStyle = col
    ctx.fillText(msg, W//2, 40)
    _no_glow()

    # score badges
    score_y = 72
    for label, cx_off, color in [
        (f"YOU  {scores['human']}", -75, "#00e5ff"),
        (f"AI  {scores['ai']}",      75, "#ff4d6d"),
    ]:
        bx = W//2 + cx_off - 38
        ctx.fillStyle = "rgba(255,255,255,0.05)"
        _rrect(bx, score_y-13, 76, 26, 8); ctx.fill()
        ctx.fillStyle = color
        ctx.font      = "bold 13px 'Segoe UI', system-ui, sans-serif"
        ctx.fillText(label, W//2 + cx_off, score_y)

    # difficulty badge
    ctx.font      = "11px 'Segoe UI', system-ui, sans-serif"
    ctx.fillStyle = "rgba(255,255,255,0.25)"
    ctx.textAlign = "right"
    ctx.fillText(current_difficulty.upper(), W - MARGIN, 18)
    ctx.textAlign = "center"

    # ── board background ──
    ctx.fillStyle = "rgba(255,255,255,0.06)"
    _rrect(MARGIN-4, OFFSET-4, 3*SQ+8, 3*SQ+8, 14)
    ctx.fill()
    ctx.strokeStyle = "rgba(255,255,255,0.20)"
    ctx.lineWidth   = 1
    ctx.stroke()

    # ── cell backgrounds ──
    for r in range(3):
        for c in range(3):
            cx2 = MARGIN + c*SQ + 4
            cy  = OFFSET + r*SQ + 4
            ctx.fillStyle = CELL_BG
            _rrect(cx2, cy, SQ-8, SQ-8, 8)
            ctx.fill()

    # ── grid lines ──
    ctx.strokeStyle = GRID_COL
    ctx.lineWidth   = 2
    ctx.lineCap     = "round"
    for i in range(1, 3):
        # horizontal
        y = OFFSET + i*SQ
        ctx.beginPath(); ctx.moveTo(MARGIN+8, y); ctx.lineTo(board_right-8, y); ctx.stroke()
        # vertical
        x = MARGIN + i*SQ
        ctx.beginPath(); ctx.moveTo(x, OFFSET+8); ctx.lineTo(x, board_bot-8); ctx.stroke()

    # ── pieces ──
    ctx.lineCap = "round"
    for r in range(3):
        for c in range(3):
            pcx, pcy = cell_center(r, c)
            v = board[r][c]
            if v == 1:   # X
                ctx.strokeStyle = X_COL; ctx.lineWidth = 7
                _glow(X_GLOW, 16)
                ctx.beginPath(); ctx.moveTo(pcx-SPACE+6, pcy-SPACE+6); ctx.lineTo(pcx+SPACE-6, pcy+SPACE-6); ctx.stroke()
                ctx.beginPath(); ctx.moveTo(pcx+SPACE-6, pcy-SPACE+6); ctx.lineTo(pcx-SPACE+6, pcy+SPACE-6); ctx.stroke()
                _no_glow()
            elif v == 2: # O
                ctx.strokeStyle = O_COL; ctx.lineWidth = 7
                _glow(O_GLOW, 16)
                ctx.beginPath(); ctx.arc(pcx, pcy, SPACE-4, 0, 2*math.pi); ctx.stroke()
                _no_glow()

    # ── win line ──
    if game_over and winner and winner != 0:
        wl = _find_win_line(board, winner)
        if wl:
            r0, c0, r1, c1 = wl
            x0, y0 = cell_center(r0, c0)
            x1, y1 = cell_center(r1, c1)
            ctx.strokeStyle = WIN_COL; ctx.lineWidth = 5
            _glow(WIN_GLOW, 22)
            ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke()
            _no_glow()

# ── State ────────────────────────────────────────────────────────────────
board        = [[0]*3 for _ in range(3)]
current_turn = 1
human_player = 1
game_over    = False
winner       = None
ai_thinking  = False
current_difficulty = "even"
scores       = {"human": 0, "ai": 0}

def get_ai_player(): return 3 - human_player

def reset_game():
    global board, current_turn, game_over, winner, ai_thinking
    board = [[0]*3 for _ in range(3)]
    current_turn = 1
    game_over = False; winner = None; ai_thinking = False

# ── Input ────────────────────────────────────────────────────────────────
def handle_click(mx, my):
    global current_turn, game_over, winner
    _unlock_voice()
    if game_over or ai_thinking or current_turn != human_player: return
    if MARGIN < mx < W-MARGIN and OFFSET < my < H-MARGIN:
        r = int((my-OFFSET)//SQ); c2 = int((mx-MARGIN)//SQ)
        if 0 <= r < 3 and 0 <= c2 < 3 and board[r][c2] == 0:
            board[r][c2] = human_player
            speak("Your move")
            if check_win(board, human_player):
                game_over=True; winner=human_player
                scores["human"] += 1
                speak("You win! Well played.")
            elif is_draw(board):
                game_over=True; winner=0; speak("It's a draw.")
            else:
                current_turn = get_ai_player()

def on_click(e):
    rect = canvas.getBoundingClientRect()
    sx = W/rect.width; sy = H/rect.height
    handle_click((e.clientX-rect.left)*sx, (e.clientY-rect.top)*sy)

def on_touch(e):
    e.preventDefault()
    t = e.changedTouches.item(0)
    rect = canvas.getBoundingClientRect()
    sx = W/rect.width; sy = H/rect.height
    handle_click((t.clientX-rect.left)*sx, (t.clientY-rect.top)*sy)

canvas.addEventListener("click",    create_proxy(on_click))
canvas.addEventListener("touchend", create_proxy(on_touch))

# ── Control handlers ──────────────────────────────────────────────────────
def on_difficulty(e):
    global current_difficulty
    current_difficulty = document.getElementById("difficulty-select").value
    reset_game()
document.getElementById("difficulty-select").addEventListener("change", create_proxy(on_difficulty))

def on_player(e):
    global human_player
    human_player = int(document.getElementById("player-select").value)
    reset_game()
document.getElementById("player-select").addEventListener("change", create_proxy(on_player))

def on_restart(e):
    reset_game()
    speak("New game.")
document.getElementById("restart-btn").addEventListener("click", create_proxy(on_restart))

# ── Main loop ─────────────────────────────────────────────────────────────
async def game_loop():
    global current_turn, game_over, winner, ai_thinking
    document.getElementById("loading").style.display = "none"
    while True:
        if current_turn == get_ai_player() and not game_over and not ai_thinking:
            ai_thinking = True
            draw()
            await asyncio.sleep(0.55)
            model = trained_models.get(current_difficulty, trained_models["even"])
            move  = get_ai_move(board, model, get_ai_player())
            if move:
                board[move[0]][move[1]] = get_ai_player()
                speak("AI plays.")
                if check_win(board, get_ai_player()):
                    game_over=True; winner=get_ai_player()
                    scores["ai"] += 1; speak("AI wins.")
                elif is_draw(board):
                    game_over=True; winner=0; speak("Draw.")
                else:
                    current_turn = human_player
            ai_thinking = False
        draw()
        await asyncio.sleep(1/30)

asyncio.ensure_future(game_loop())
