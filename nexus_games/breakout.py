import asyncio, random, math, time
from js import document
from pyodide.ffi import create_proxy

canvas=document.getElementById("gameCanvas")
ctx=canvas.getContext("2d")
W,H=380,500
PAD_W=74; PAD_H=13; PAD_Y=H-34; BALL_R=8

BRICK_ROWS=6; BRICK_COLS=8
BW=(W-24)//(BRICK_COLS); BH=16; B_OFF_X=12; B_OFF_Y=55
BRICK_COLORS=[
    ["#ff2d6e","#ff4d84","#ff2d6e","#ff4d84","#ff2d6e","#ff4d84","#ff2d6e","#ff4d84"],
    ["#ff6b2d","#ff8a4d","#ff6b2d","#ff8a4d","#ff6b2d","#ff8a4d","#ff6b2d","#ff8a4d"],
    ["#ffb52d","#ffc84d","#ffb52d","#ffc84d","#ffb52d","#ffc84d","#ffb52d","#ffc84d"],
    ["#d4ff2d","#e2ff4d","#d4ff2d","#e2ff4d","#d4ff2d","#e2ff4d","#d4ff2d","#e2ff4d"],
    ["#2dff8a","#4dffaa","#2dff8a","#4dffaa","#2dff8a","#4dffaa","#2dff8a","#4dffaa"],
    ["#2d8aff","#4daaff","#2d8aff","#4daaff","#2d8aff","#4daaff","#2d8aff","#4daaff"],
]
BRICK_PTS=[60,50,40,30,20,10]

pad_x=W//2; ball_x=W//2; ball_y=H-60
bvx=3.5; bvy=-4.0; launched=False
bricks=[]; score=0; lives=3; level=1; won=False; dead=False
particles=[]; trail=[]
mouse_x=W//2
combo=0; combo_t=0.0   # combo counter

def make_bricks():
    global bricks
    bricks=[]
    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS):
            bx=B_OFF_X+c*(BW+2); by=B_OFF_Y+r*(BH+4)
            hits=2 if r<2 else 1   # top 2 rows need 2 hits
            col=BRICK_COLORS[r][c]
            bricks.append({"x":bx,"y":by,"w":BW,"h":BH,"col":col,"pts":BRICK_PTS[r],"hits":hits,"max_hits":hits})

def reset_ball():
    global ball_x,ball_y,bvx,bvy,launched,combo
    ball_x=pad_x; ball_y=PAD_Y-BALL_R-6
    angle=random.uniform(-0.6,0.6)
    speed=4.0+level*0.5
    bvx=math.sin(angle)*speed; bvy=-abs(math.cos(angle))*speed
    launched=False; combo=0

def add_particle(x,y,col,n=10):
    for _ in range(n):
        a=random.uniform(0,math.pi*2); s=random.uniform(2,6)
        particles.append({"x":x,"y":y,"vx":math.cos(a)*s,"vy":math.sin(a)*s,"life":1.0,"col":col,"r":random.uniform(2,4)})

def add_trail(x,y):
    trail.append({"x":x,"y":y,"life":0.4})

def update_particles(dt):
    for p in particles: p["x"]+=p["vx"]*dt*60; p["y"]+=p["vy"]*dt*60; p["life"]-=dt*2.8
    particles[:]=[ p for p in particles if p["life"]>0]
    for t2 in trail: t2["life"]-=dt*3
    trail[:]=[ t2 for t2 in trail if t2["life"]>0]

def draw():
    ctx.fillStyle="#04060f"; ctx.fillRect(0,0,W,H)
    # Subtle grid
    ctx.strokeStyle="rgba(77,143,255,.04)"; ctx.lineWidth=1
    for x in range(0,W,28): ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()
    for y in range(0,H,28): ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()
    # Ball trail
    for t2 in trail:
        ctx.globalAlpha=t2["life"]*0.4
        ctx.fillStyle="rgba(255,255,255,.6)"
        ctx.beginPath(); ctx.arc(t2["x"],t2["y"],BALL_R*0.5,0,math.pi*2); ctx.fill()
    ctx.globalAlpha=1
    # Bricks
    for b in bricks:
        if b["hits"]<=0: continue
        col=b["col"]
        # Darken if damaged
        if b["hits"]<b["max_hits"]: col="#555"
        ctx.fillStyle=col
        ctx.shadowColor=col; ctx.shadowBlur=6
        ctx.beginPath(); ctx.roundRect(b["x"],b["y"],b["w"],b["h"],3); ctx.fill()
        ctx.shadowBlur=0
        # Gloss
        ctx.fillStyle="rgba(255,255,255,.1)"
        ctx.beginPath(); ctx.roundRect(b["x"]+2,b["y"]+2,b["w"]-4,(b["h"]//2)-2,2); ctx.fill()
    # Particles
    for p in particles:
        ctx.globalAlpha=p["life"]; ctx.fillStyle=p["col"]
        ctx.shadowColor=p["col"]; ctx.shadowBlur=4
        ctx.beginPath(); ctx.arc(p["x"],p["y"],p["r"],0,math.pi*2); ctx.fill()
    ctx.globalAlpha=1; ctx.shadowBlur=0
    # Paddle — glow
    ctx.fillStyle="#00e87a"; ctx.shadowColor="#00e87a"; ctx.shadowBlur=18
    ctx.beginPath(); ctx.roundRect(pad_x-PAD_W//2,PAD_Y-PAD_H//2,PAD_W,PAD_H,6); ctx.fill()
    # Paddle highlight
    ctx.fillStyle="rgba(255,255,255,.25)"
    ctx.beginPath(); ctx.roundRect(pad_x-PAD_W//2+4,PAD_Y-PAD_H//2+2,PAD_W-8,4,2); ctx.fill()
    ctx.shadowBlur=0
    # Ball
    ctx.fillStyle="white"; ctx.shadowColor="rgba(200,240,255,.9)"; ctx.shadowBlur=14
    ctx.beginPath(); ctx.arc(ball_x,ball_y,BALL_R,0,math.pi*2); ctx.fill()
    ctx.shadowBlur=0
    # Combo
    if combo>=3 and combo_t>0:
        ctx.fillStyle=f"rgba(255,200,50,{min(1,combo_t*3)})"
        ctx.font="bold 14px monospace"; ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText(f"COMBO x{combo}!",W//2,PAD_Y-50)
    # Launch hint
    if not launched and not dead and not won:
        ctx.fillStyle="rgba(0,232,122,.9)"; ctx.font="bold 14px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("SPACE or TAP to launch",W//2,PAD_Y-36)
    if dead or won:
        ctx.fillStyle="rgba(2,6,14,.88)"; ctx.fillRect(0,0,W,H)
        col="#ffe050" if won else "#ff2d6e"
        ctx.fillStyle=col; ctx.font="bold 28px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("YOU WIN! 🎉" if won else "GAME OVER",W//2,H//2-22)
        ctx.fillStyle="#7888a8"; ctx.font="14px monospace"
        ctx.fillText(f"Score: {score}",W//2,H//2+8)
        ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
        ctx.fillText("Space or tap to restart",W//2,H//2+28)

def restart():
    global score,lives,level,won,dead,particles,launched,pad_x,trail,combo,combo_t
    score=0; lives=3; level=1; won=False; dead=False; particles=[]; trail=[]; combo=0; combo_t=0
    document.getElementById("s-score").textContent="0"
    document.getElementById("s-lives").textContent="3"
    document.getElementById("s-level").textContent="1"
    pad_x=W//2; make_bricks(); reset_ball()

def on_mouse(e):
    global mouse_x,pad_x
    rect=canvas.getBoundingClientRect()
    mouse_x=e.clientX-rect.left
    pad_x=max(PAD_W//2, min(W-PAD_W//2, int(mouse_x)))
    if not launched: reset_ball()

def on_touch_m(e):
    global mouse_x,pad_x
    t=e.touches.item(0); rect=canvas.getBoundingClientRect()
    mouse_x=t.clientX-rect.left
    pad_x=max(PAD_W//2, min(W-PAD_W//2, int(mouse_x)))
    if not launched: reset_ball()

def on_key(e):
    global launched
    if e.key==" ":
        e.preventDefault()
        if dead or won: restart()
        else: launched=True

def on_click(e):
    global launched
    if dead or won: restart()
    else: launched=True

canvas.addEventListener("mousemove",create_proxy(on_mouse))
canvas.addEventListener("touchmove",create_proxy(on_touch_m),{"passive":True})
canvas.addEventListener("click",create_proxy(on_click))
canvas.addEventListener("touchend",create_proxy(on_click))
document.addEventListener("keydown",create_proxy(on_key))

async def game_loop():
    global ball_x,ball_y,bvx,bvy,score,lives,level,won,dead,pad_x,combo,combo_t
    import time as tm
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"
    last=tm.time()
    while True:
        now=tm.time(); dt=min(now-last,.05); last=now
        update_particles(dt)
        if combo_t>0: combo_t-=dt
        if launched and not dead and not won:
            # Sub-step for accuracy
            steps=3
            sdx=bvx/steps; sdy=bvy/steps
            for _ in range(steps):
                ball_x+=sdx; ball_y+=sdy
                add_trail(ball_x,ball_y)
                # Walls
                if ball_x<=BALL_R: ball_x=BALL_R; bvx=abs(bvx)
                if ball_x>=W-BALL_R: ball_x=W-BALL_R; bvx=-abs(bvx)
                if ball_y<=BALL_R: ball_y=BALL_R; bvy=abs(bvy)
                # Paddle collision
                if (bvy>0 and PAD_Y-PAD_H//2-BALL_R<=ball_y<=PAD_Y+PAD_H//2
                        and pad_x-PAD_W//2-BALL_R<=ball_x<=pad_x+PAD_W//2+BALL_R):
                    off=(ball_x-pad_x)/(PAD_W//2)
                    speed=math.sqrt(bvx**2+bvy**2)
                    bvx=off*speed*1.2; bvy=-abs(bvy)
                    combo=0  # reset combo on paddle hit
                # Bottom
                if ball_y>H+BALL_R:
                    lives-=1; document.getElementById("s-lives").textContent=str(lives)
                    if lives<=0: dead=True
                    else: reset_ball()
                    break
                # Bricks
                for b in bricks:
                    if b["hits"]<=0: continue
                    if (b["x"]-BALL_R<=ball_x<=b["x"]+b["w"]+BALL_R and
                            b["y"]-BALL_R<=ball_y<=b["y"]+b["h"]+BALL_R):
                        b["hits"]-=1
                        if b["hits"]<=0:
                            combo+=1; combo_t=1.5
                            pts=b["pts"]*(1+combo//5)
                            score+=pts
                            document.getElementById("s-score").textContent=str(score)
                            add_particle(ball_x,ball_y,b["col"],10)
                        else:
                            add_particle(ball_x,ball_y,"#ffffff",4)
                        # Bounce side
                        if ball_y<b["y"] or ball_y>b["y"]+b["h"]: bvy*=-1
                        else: bvx*=-1
                        break
            # All bricks cleared?
            if all(b["hits"]<=0 for b in bricks):
                level+=1; document.getElementById("s-level").textContent=str(level)
                if level>4: won=True
                else: make_bricks(); reset_ball()
        draw()
        await asyncio.sleep(1/60)

make_bricks(); reset_ball()
asyncio.ensure_future(game_loop())
