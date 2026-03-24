import asyncio, random, math
from js import document, window
from pyodide.ffi import create_proxy

canvas = document.getElementById("gameCanvas")
ctx    = canvas.getContext("2d")
W, H   = 320, 320
CELL   = 16
COLS   = W // CELL
ROWS   = H // CELL

snake   = []
sdir    = (1,0)
snxt    = (1,0)
food    = (0,0)
bonus   = None       # bonus food (purple, +30)
bonus_t = 0.0
score   = 0
best    = 0
alive   = False
tx = ty = 0
speed_lvl = 1        # increases every 5 foods eaten
foods_eaten = 0
particles   = []

def reset():
    global snake,sdir,snxt,food,score,alive,speed_lvl,foods_eaten,bonus,bonus_t,particles
    cx,cy = COLS//2, ROWS//2
    snake = [(cx,cy),(cx-1,cy),(cx-2,cy)]
    sdir=snxt=(1,0); score=0; alive=False
    speed_lvl=1; foods_eaten=0; bonus=None; bonus_t=0; particles=[]
    spawn_food(); draw()

def spawn_food():
    global food
    while True:
        p=(random.randint(0,COLS-1), random.randint(0,ROWS-1))
        if p not in snake: food=p; break

def spawn_bonus():
    global bonus, bonus_t
    while True:
        p=(random.randint(0,COLS-1), random.randint(0,ROWS-1))
        if p not in snake and p!=food: bonus=p; bonus_t=8.0; break

def add_particle(x,y,col,n=6):
    for _ in range(n):
        a=random.uniform(0,math.pi*2); s=random.uniform(2,5)
        particles.append({"x":x*CELL+CELL//2,"y":y*CELL+CELL//2,
                          "vx":math.cos(a)*s,"vy":math.sin(a)*s,"life":1.0,"col":col})

def change_dir(dx,dy):
    global snxt,alive
    if not alive: alive=True; return
    if dx!=0 and sdir[0]==0: snxt=(dx,0)
    elif dy!=0 and sdir[1]==0: snxt=(0,dy)

def tick():
    global snake,sdir,snxt,food,score,best,alive,speed_lvl,foods_eaten,bonus,bonus_t
    if not alive: return
    sdir = snxt
    hx,hy = snake[0]; head=(hx+sdir[0], hy+sdir[1])
    if head[0]<0 or head[0]>=COLS or head[1]<0 or head[1]>=ROWS or head in snake:
        alive=False; return
    snake.insert(0,head)
    ate=False
    if head==food:
        score+=10; ate=True
        foods_eaten+=1
        if foods_eaten%5==0: speed_lvl+=1
        if foods_eaten%7==0 and bonus is None: spawn_bonus()
        spawn_food(); add_particle(head[0],head[1],"#ff2d6e",8)
    elif bonus and head==bonus:
        score+=30; ate=True; bonus=None; add_particle(head[0],head[1],"#bf5fff",12)
    if ate:
        best=max(best,score)
        document.getElementById("score-val").textContent=str(score)
        document.getElementById("best-val").textContent=str(best)
    else:
        snake.pop()

def draw():
    ctx.fillStyle="#02060e"; ctx.fillRect(0,0,W,H)
    # Grid
    ctx.strokeStyle="rgba(0,255,136,.035)"; ctx.lineWidth=.5
    for x in range(0,W,CELL): ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()
    for y in range(0,H,CELL): ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()
    # Bonus food (pulsing purple)
    if bonus:
        pulse=0.7+0.3*math.sin(bonus_t*6)
        bx,by=bonus
        ctx.fillStyle=f"rgba(191,95,255,{pulse})"
        ctx.shadowColor="#bf5fff"; ctx.shadowBlur=12
        ctx.beginPath(); ctx.arc(bx*CELL+CELL//2,by*CELL+CELL//2,CELL//2-1,0,2*math.pi); ctx.fill()
        ctx.shadowBlur=0
    # Food
    fx,fy=food
    ctx.fillStyle="#ff2d6e"; ctx.shadowColor="#ff2d6e"; ctx.shadowBlur=10
    ctx.beginPath(); ctx.arc(fx*CELL+CELL//2,fy*CELL+CELL//2,CELL//2-2,0,2*math.pi); ctx.fill()
    ctx.shadowBlur=0
    # Particles
    for p in particles:
        ctx.globalAlpha=p["life"]; ctx.fillStyle=p["col"]
        ctx.beginPath(); ctx.arc(p["x"],p["y"],3,0,math.pi*2); ctx.fill()
    ctx.globalAlpha=1
    # Snake — gradient from head to tail
    n=len(snake)
    for i,(sx,sy) in enumerate(snake):
        t2=i/max(n-1,1)
        r=int(0 + t2*0); g=int(255 - t2*155); b=int(136 - t2*100)
        ctx.fillStyle=f"rgb({r},{g},{b})"
        ctx.shadowColor="#00ff88" if i==0 else "transparent"
        ctx.shadowBlur=8 if i==0 else 0
        ctx.fillRect(sx*CELL+2,sy*CELL+2,CELL-4,CELL-4)
    ctx.shadowBlur=0
    # Speed indicator dots
    for i in range(speed_lvl):
        ctx.fillStyle=["#00e87a","#ffe050","#ff8c00","#ff2d6e"][min(i,3)]
        ctx.beginPath(); ctx.arc(8+i*12,H-8,4,0,math.pi*2); ctx.fill()
    # Overlay
    if not alive:
        ctx.fillStyle="rgba(2,6,14,.85)"; ctx.fillRect(0,0,W,H)
        ctx.fillStyle="#00ff88"; ctx.font="bold 26px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("SNAKE" if score==0 else "GAME OVER",W//2,H//2-24)
        ctx.fillStyle="#7888a8"; ctx.font="13px monospace"
        if score==0:
            ctx.fillText("Tap D-pad or press Arrow keys",W//2,H//2+8)
        else:
            ctx.fillText(f"Score: {score}",W//2,H//2+8)
            ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
            ctx.fillText("R to restart",W//2,H//2+28)

# ── Input ──
def on_key(e):
    k=e.key
    if k=="r" or k=="R": reset(); return
    m={"ArrowUp":(0,-1),"ArrowDown":(0,1),"ArrowLeft":(-1,0),"ArrowRight":(1,0),
       "w":(0,-1),"s":(0,1),"a":(-1,0),"d":(1,0)," ":(0,0)}
    if k in m:
        e.preventDefault()
        if k==" ": change_dir(0,0)
        else: change_dir(*m[k])
document.addEventListener("keydown", create_proxy(on_key))

def on_ts(e):
    global tx,ty
    t=e.touches.item(0); tx=t.clientX; ty=t.clientY
def on_te(e):
    t=e.changedTouches.item(0)
    dx=t.clientX-tx; dy=t.clientY-ty
    if abs(dx)<8 and abs(dy)<8: change_dir(0,0); return
    if abs(dx)>abs(dy): change_dir(1 if dx>0 else -1, 0)
    else: change_dir(0, 1 if dy>0 else -1)
canvas.addEventListener("touchstart",create_proxy(on_ts),{"passive":True})
canvas.addEventListener("touchend",create_proxy(on_te),{"passive":True})

def make_dpad(dx,dy):
    def h(e): change_dir(dx,dy)
    return create_proxy(h)
for bid,dx,dy in [("btn-up",0,-1),("btn-down",0,1),("btn-left",-1,0),("btn-right",1,0)]:
    el=document.getElementById(bid)
    el.addEventListener("touchstart",make_dpad(dx,dy),{"passive":True})
    el.addEventListener("mousedown", make_dpad(dx,dy))

async def game_loop():
    global bonus_t
    import time as tm
    # Fade out loading
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"

    last=tm.time(); frame=0
    while True:
        now=tm.time(); dt=min(now-last,.05); last=now
        # Update bonus timer
        if bonus is not None:
            bonus_t-=dt
            if bonus_t<=0:
                global bonus
                bonus=None
        # Particles
        for p in particles: p["x"]+=p["vx"]*dt*60; p["y"]+=p["vy"]*dt*60; p["life"]-=dt*2.5
        particles[:]=[ p for p in particles if p["life"]>0]
        # Tick rate scales with speed level
        tick_every=max(3, 7-speed_lvl)
        frame+=1
        if frame>=tick_every: tick(); frame=0
        draw()
        await asyncio.sleep(1/60)

reset()
asyncio.ensure_future(game_loop())
