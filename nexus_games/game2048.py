import asyncio, random, copy, math
from js import document
from pyodide.ffi import create_proxy

canvas=document.getElementById("gameCanvas")
ctx=canvas.getContext("2d")
W,H=380,380
GRID=4; GAP=10
CELL=(W-GAP*(GRID+1))//GRID

TCOLS={
    0:"#0d1628",
    2:"#1a3060",4:"#1e3880",
    8:"#e07020",16:"#e05010",
    32:"#e03000",64:"#d02000",
    128:"#9040e0",256:"#7020d0",
    512:"#00c8e8",1024:"#00a0c0",
    2048:"#ffe040",
}
TTEXT_DARK={0,2,4}  # tiles where text should be muted

board=[[0]*GRID for _ in range(GRID)]
prev_board=None; score=0; best=0; won=False; over=False
tx=ty=0
# Tile animations: {(r,c): {"scale": float, "alpha": float}}
tile_anims={}
score_pop=[]  # floating +score texts

def add_tile():
    empty=[(r,c) for r in range(GRID) for c in range(GRID) if board[r][c]==0]
    if not empty: return
    r,c=random.choice(empty)
    board[r][c]=2 if random.random()<.9 else 4
    tile_anims[(r,c)]={"scale":0.1,"alpha":0}

def slide_row(row):
    r=[v for v in row if v]; gained=0; i=0
    while i<len(r)-1:
        if r[i]==r[i+1]: r[i]*=2; gained+=r[i]; del r[i+1]
        i+=1
    while len(r)<GRID: r.append(0)
    return r, gained

def move(direction):
    global prev_board,score,best,won,over
    if over: return
    prev_board=copy.deepcopy(board); moved=False; g=0
    if direction=="left":
        for r in range(GRID):
            nr,gn=slide_row(board[r])
            if nr!=board[r]: moved=True
            board[r]=nr; g+=gn
    elif direction=="right":
        for r in range(GRID):
            nr,gn=slide_row(board[r][::-1]); nr=nr[::-1]
            if nr!=board[r]: moved=True
            board[r]=nr; g+=gn
    elif direction=="up":
        for c in range(GRID):
            col=[board[r][c] for r in range(GRID)]
            nc2,gn=slide_row(col)
            for r in range(GRID):
                if board[r][c]!=nc2[r]: moved=True
                board[r][c]=nc2[r]
            g+=gn
    elif direction=="down":
        for c in range(GRID):
            col=[board[r][c] for r in range(GRID)][::-1]
            nc2,gn=slide_row(col); nc2=nc2[::-1]
            for r in range(GRID):
                if board[r][c]!=nc2[r]: moved=True
                board[r][c]=nc2[r]
            g+=gn
    if moved:
        score+=g; best=max(best,score)
        document.getElementById("s-score").textContent=str(score)
        document.getElementById("s-best").textContent=str(best)
        if g>0:
            # Score pop-up at random merged tile position
            r2=random.randint(0,GRID-1); c2=random.randint(0,GRID-1)
            bx=GAP+c2*(CELL+GAP)+CELL//2; by=GAP+r2*(CELL+GAP)+CELL//2
            score_pop.append({"x":bx,"y":by,"txt":f"+{g}","life":1.2,"vy":-1.5})
        add_tile()
        if any(2048 in row for row in board): won=True
        elif not can_move(): over=True

def undo():
    global board,prev_board,over
    if prev_board: board=prev_board; prev_board=None; over=False

def can_move():
    for r in range(GRID):
        for c in range(GRID):
            if board[r][c]==0: return True
            if c<GRID-1 and board[r][c]==board[r][c+1]: return True
            if r<GRID-1 and board[r][c]==board[r+1][c]: return True
    return False

def reset():
    global board,prev_board,score,won,over,tile_anims,score_pop
    board=[[0]*GRID for _ in range(GRID)]
    prev_board=None; score=0; won=False; over=False
    tile_anims={}; score_pop=[]
    document.getElementById("s-score").textContent="0"
    add_tile(); add_tile()

def tile_font_size(v):
    if v<100: return 26
    if v<1000: return 20
    return 14

def draw():
    ctx.fillStyle="#060a18"; ctx.fillRect(0,0,W,H)
    # Board bg
    ctx.fillStyle="#0a1228"
    ctx.beginPath(); ctx.roundRect(GAP//2,GAP//2,W-GAP,H-GAP,10); ctx.fill()
    # Grid slots
    for r in range(GRID):
        for c in range(GRID):
            bx=GAP+c*(CELL+GAP); by=GAP+r*(CELL+GAP)
            ctx.fillStyle="#0d1630"
            ctx.beginPath(); ctx.roundRect(bx,by,CELL,CELL,7); ctx.fill()
    # Tiles
    for r in range(GRID):
        for c in range(GRID):
            v=board[r][c]
            bx=GAP+c*(CELL+GAP); by=GAP+r*(CELL+GAP)
            col=TCOLS.get(v,TCOLS[2048])
            # Animate new tiles
            anim=tile_anims.get((r,c))
            sc=anim["scale"] if anim else 1.0
            cx2=bx+CELL//2; cy2=by+CELL//2
            sw=int(CELL*sc); sh=int(CELL*sc)
            ax=cx2-sw//2; ay=cy2-sh//2
            ctx.fillStyle=col
            if v>0:
                ctx.shadowColor=col; ctx.shadowBlur=8 if v>=64 else 0
                ctx.beginPath(); ctx.roundRect(ax,ay,sw,sh,7); ctx.fill()
                ctx.shadowBlur=0
                # Highlight top edge
                ctx.fillStyle="rgba(255,255,255,.08)"
                ctx.beginPath(); ctx.roundRect(ax+2,ay+2,sw-4,min(8,sh//3),3); ctx.fill()
                if sc>0.5:
                    text_col="rgba(255,255,255,.95)" if v not in TTEXT_DARK else "rgba(255,255,255,.5)"
                    ctx.fillStyle=text_col
                    ctx.textAlign="center"; ctx.textBaseline="middle"
                    ctx.font=f"bold {tile_font_size(v)}px monospace"
                    ctx.fillText(str(v),cx2,cy2)
    # Score pops
    for sp in score_pop:
        ctx.globalAlpha=sp["life"]
        ctx.fillStyle="#ffe050"; ctx.font="bold 14px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText(sp["txt"],sp["x"],sp["y"])
    ctx.globalAlpha=1
    if won or over:
        ctx.fillStyle="rgba(2,6,14,.82)"; ctx.fillRect(0,0,W,H)
        col="#ffe050" if won else "#ff2d6e"
        ctx.fillStyle=col; ctx.font="bold 28px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("YOU WIN! 🎉" if won else "GAME OVER",W//2,H//2-20)
        ctx.fillStyle="#7888a8"; ctx.font="14px monospace"
        ctx.fillText(f"Score: {score}",W//2,H//2+8)
        ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
        ctx.fillText("Press New Game to retry",W//2,H//2+28)

def on_key(e):
    k=e.key
    m={"ArrowLeft":"left","ArrowRight":"right","ArrowUp":"up","ArrowDown":"down",
       "a":"left","d":"right","w":"up","s":"down"}
    if k in m: e.preventDefault(); move(m[k])
    elif k=="u" or k=="U": undo()
    elif k=="r" or k=="R": reset()
document.addEventListener("keydown",create_proxy(on_key))

def on_ts(e):
    global tx,ty
    t=e.touches.item(0); tx=t.clientX; ty=t.clientY
def on_te(e):
    t=e.changedTouches.item(0)
    dx=t.clientX-tx; dy=t.clientY-ty
    if abs(dx)>abs(dy): move("right" if dx>0 else "left")
    else: move("down" if dy>0 else "up")
canvas.addEventListener("touchstart",create_proxy(on_ts),{"passive":True})
canvas.addEventListener("touchend",create_proxy(on_te),{"passive":True})
document.getElementById("undo-btn").addEventListener("click",create_proxy(lambda e:undo()))
document.getElementById("reset-btn").addEventListener("click",create_proxy(lambda e:reset()))

async def game_loop():
    import time as tm
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"
    last=tm.time()
    while True:
        now=tm.time(); dt=now-last; last=now
        # Animate new tiles
        for key in list(tile_anims.keys()):
            a=tile_anims[key]
            a["scale"]=min(1.0,a["scale"]+dt*7)
            a["alpha"]=a["scale"]
            if a["scale"]>=1.0: del tile_anims[key]
        # Score pops
        for sp in score_pop:
            sp["y"]+=sp["vy"]*dt*60; sp["life"]-=dt*2
        score_pop[:]=[sp for sp in score_pop if sp["life"]>0]
        draw()
        await asyncio.sleep(1/30)

reset()
asyncio.ensure_future(game_loop())
