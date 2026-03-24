import asyncio, random, math
from js import document
from pyodide.ffi import create_proxy

canvas = document.getElementById("gameCanvas")
ctx    = canvas.getContext("2d")
nc     = document.getElementById("nextCanvas")
nctx   = nc.getContext("2d")
W,H    = 200,400
COLS,ROWS,BS = 10,20,20

PIECES=[
    {"s":[[1,1,1,1]],         "c":"#00f0ff"},
    {"s":[[1,1],[1,1]],       "c":"#ffe066"},
    {"s":[[0,1,0],[1,1,1]],   "c":"#bf5fff"},
    {"s":[[1,0],[1,0],[1,1]], "c":"#ff8c00"},
    {"s":[[0,1],[0,1],[1,1]], "c":"#00ff88"},
    {"s":[[0,1,1],[1,1,0]],   "c":"#ff2d6e"},
    {"s":[[1,1,0],[0,1,1]],   "c":"#4d8fff"},
]
LINE_SC=[0,100,300,500,800]

# 7-bag randomizer
piece_bag=[]
def next_from_bag():
    global piece_bag
    if not piece_bag: piece_bag=list(range(len(PIECES))); random.shuffle(piece_bag)
    return piece_bag.pop()

def rot(s): return [list(r) for r in zip(*s[::-1])]
def new_piece():
    idx=next_from_bag(); p=PIECES[idx]
    return {"s":[r[:] for r in p["s"]],"c":p["c"],"x":COLS//2-len(p["s"][0])//2,"y":0}

board  = [[None]*COLS for _ in range(ROWS)]
piece  = new_piece()
nxt    = new_piece()
score=lines=0; level=1; alive=True; paused=False
fall_t=0; fall_spd=0.5
tx=ty=0
line_flash=[]   # rows currently flashing
flash_t=0
particles=[]

def calc_spd(): return max(0.065, 0.5-level*0.045)

def collides(p,dx=0,dy=0,sh=None):
    s=sh or p["s"]
    for r,row in enumerate(s):
        for c,v in enumerate(row):
            if not v: continue
            nx,ny=p["x"]+c+dx,p["y"]+r+dy
            if nx<0 or nx>=COLS or ny>=ROWS: return True
            if ny>=0 and board[ny][nx]: return True
    return False

def add_particles(row,col_str):
    import math as m
    for _ in range(6):
        a=m.uniform(0,m.pi*2); s=m.uniform(2,5)
        particles.append({"x":(random.randint(0,COLS-1))*BS+BS//2,"y":row*BS+BS//2,
                          "vx":m.cos(a)*s,"vy":m.sin(a)*s,"life":1.0,"col":col_str})

def lock():
    global piece,nxt,score,lines,level,alive,fall_spd,line_flash,flash_t
    for r,row in enumerate(piece["s"]):
        for c,v in enumerate(row):
            if v:
                y2=piece["y"]+r
                if y2<0: alive=False; return
                board[y2][piece["x"]+c]=piece["c"]
    # Find complete rows
    complete=[i for i,row in enumerate(board) if all(cell is not None for cell in row)]
    if complete:
        line_flash=complete; flash_t=0.18
        for r in complete: add_particles(r,"#00e87a")
    else:
        _finish_lock(0)

def _finish_lock(cleared_count):
    global piece,nxt,score,lines,level,alive,fall_spd,line_flash
    cleared=len(line_flash)
    if cleared:
        new_board=[row for i,row in enumerate(board) if i not in line_flash]
        for _ in range(cleared): new_board.insert(0,[None]*COLS)
        board[:]=new_board
        lines+=cleared; score+=LINE_SC[min(cleared,4)]*level
        level=lines//10+1; fall_spd=calc_spd()
        document.getElementById("s-score").textContent=str(score)
        document.getElementById("s-lines").textContent=str(lines)
        document.getElementById("s-level").textContent=str(level)
    line_flash=[]
    piece=nxt; nxt=new_piece()
    if collides(piece): alive=False

def ghost_y():
    gy=piece["y"]
    while not collides(piece,dy=gy-piece["y"]+1): gy+=1
    return gy

def draw_block(ct,gx,gy,col,cell=BS,alpha=1.0):
    r=int(col[1:3],16); g=int(col[3:5],16); b=int(col[5:7],16)
    ct.fillStyle=f"rgba({r},{g},{b},{alpha})"
    ct.shadowColor=col; ct.shadowBlur=5 if alpha==1.0 else 0
    ct.fillRect(gx*cell+1,gy*cell+1,cell-2,cell-2)
    # highlight edge
    if alpha==1.0:
        ct.fillStyle=f"rgba(255,255,255,.12)"
        ct.fillRect(gx*cell+1,gy*cell+1,cell-2,3)
    ct.shadowBlur=0

def draw():
    ctx.fillStyle="#02060e"; ctx.fillRect(0,0,W,H)
    ctx.strokeStyle="rgba(0,200,255,.03)"; ctx.lineWidth=.5
    for x in range(COLS): ctx.beginPath();ctx.moveTo(x*BS,0);ctx.lineTo(x*BS,H);ctx.stroke()
    for y in range(ROWS): ctx.beginPath();ctx.moveTo(0,y*BS);ctx.lineTo(W,y*BS);ctx.stroke()
    # Board
    for r,row in enumerate(board):
        if r in line_flash:
            ctx.fillStyle="rgba(255,255,255,.7)"; ctx.fillRect(0,r*BS,W,BS)
            continue
        for c,col in enumerate(row):
            if col: draw_block(ctx,c,r,col)
    # Ghost
    if alive and not paused:
        gy=ghost_y()
        for r,row in enumerate(piece["s"]):
            for c,v in enumerate(row):
                if v: draw_block(ctx,piece["x"]+c,gy+r,piece["c"],alpha=0.12)
    # Active piece
    if alive and not paused:
        for r,row in enumerate(piece["s"]):
            for c,v in enumerate(row):
                if v: draw_block(ctx,piece["x"]+c,piece["y"]+r,piece["c"])
    # Particles
    for p in particles:
        ctx.globalAlpha=p["life"]; ctx.fillStyle=p["col"]
        ctx.beginPath(); ctx.arc(p["x"],p["y"],3,0,math.pi*2); ctx.fill()
    ctx.globalAlpha=1
    # Overlay
    if not alive or paused:
        ctx.fillStyle="rgba(2,6,14,.88)"; ctx.fillRect(0,0,W,H)
        col="#00f0ff" if paused else "#ff2d6e"
        ctx.fillStyle=col; ctx.font="bold 22px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("PAUSED" if paused else "GAME OVER",W//2,H//2-18)
        ctx.fillStyle="#7888a8"; ctx.font="13px monospace"
        ctx.fillText("P resume" if paused else f"Score {score}",W//2,H//2+8)
        if not paused:
            ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
            ctx.fillText("R to restart",W//2,H//2+26)
    # Next
    nctx.fillStyle="#02060e"; nctx.fillRect(0,0,84,84)
    nb=16; s=nxt["s"]
    ox=(84-len(s[0])*nb)//2; oy=(84-len(s)*nb)//2
    for r,row in enumerate(s):
        for c,v in enumerate(row):
            if v:
                nctx.fillStyle=nxt["c"]; nctx.shadowColor=nxt["c"]; nctx.shadowBlur=6
                nctx.fillRect(ox+c*nb+1,oy+r*nb+1,nb-2,nb-2); nctx.shadowBlur=0

def move(dx):
    if alive and not paused and not collides(piece,dx=dx): piece["x"]+=dx
def rotate():
    if not alive or paused: return
    r=rot(piece["s"])
    # Wall kick
    for kick in [0,-1,1,-2,2]:
        if not collides(piece,dx=kick,sh=r): piece["s"]=r; piece["x"]+=kick; return
def soft():
    if alive and not paused:
        if not collides(piece,dy=1): piece["y"]+=1
        else: lock()
def hard():
    if not alive or paused: return
    while not collides(piece,dy=1): piece["y"]+=1
    lock()

def do_restart():
    global board,piece,nxt,score,lines,level,fall_spd,alive,paused,piece_bag,particles,line_flash
    board=[[None]*COLS for _ in range(ROWS)]
    piece_bag=[]; piece=new_piece(); nxt=new_piece()
    score=lines=0; level=1; alive=True; paused=False; fall_spd=calc_spd()
    particles=[]; line_flash=[]
    document.getElementById("s-score").textContent="0"
    document.getElementById("s-lines").textContent="0"
    document.getElementById("s-level").textContent="1"

def on_key(e):
    k=e.key
    if k=="p" or k=="P":
        global paused; paused = not paused; return
    if k=="r" or k=="R": do_restart(); return
    if k==" ": e.preventDefault(); hard()
    elif k=="ArrowLeft" or k=="a": move(-1)
    elif k=="ArrowRight" or k=="d": move(1)
    elif k=="ArrowDown" or k=="s": soft()
    elif k=="ArrowUp" or k=="w": rotate()
document.addEventListener("keydown",create_proxy(on_key))

for bid,fn in [("mb-left",lambda e:move(-1)),("mb-right",lambda e:move(1)),
               ("mb-rot",lambda e:rotate()),("mb-down",lambda e:soft()),("mb-drop",lambda e:hard())]:
    document.getElementById(bid).addEventListener("touchstart",create_proxy(fn),{"passive":True})
    document.getElementById(bid).addEventListener("mousedown",create_proxy(fn))

def on_ts(e):
    global tx,ty
    t=e.touches.item(0); tx=t.clientX; ty=t.clientY
def on_te(e):
    t=e.changedTouches.item(0)
    dx=t.clientX-tx; dy=t.clientY-ty
    if abs(dx)<10 and abs(dy)<10: rotate(); return
    if abs(dx)>abs(dy): move(1 if dx>0 else -1)
    elif dy>15: hard()
    else: rotate()
canvas.addEventListener("touchstart",create_proxy(on_ts),{"passive":True})
canvas.addEventListener("touchend",create_proxy(on_te),{"passive":True})

async def game_loop():
    global fall_t, flash_t, line_flash
    import time
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"
    last=time.time()
    while True:
        now=time.time(); dt=now-last; last=now
        # Particles
        for p in particles: p["x"]+=p["vx"]*dt*60; p["y"]+=p["vy"]*dt*60; p["life"]-=dt*3
        particles[:]=[p for p in particles if p["life"]>0]
        # Flash
        if flash_t>0:
            flash_t-=dt
            if flash_t<=0: _finish_lock(0)
        if alive and not paused and not line_flash:
            fall_t+=dt
            if fall_t>=fall_spd:
                fall_t=0
                if not collides(piece,dy=1): piece["y"]+=1
                else: lock()
        draw()
        await asyncio.sleep(1/60)

asyncio.ensure_future(game_loop())
