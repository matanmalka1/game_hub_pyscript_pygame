import asyncio, random, math, time
from js import document
from pyodide.ffi import create_proxy

canvas=document.getElementById("gameCanvas")
ctx=canvas.getContext("2d")
W,H=380,500

player={"x":W//2,"y":H-44,"w":32,"h":22,"speed":5}
p_bullets=[]; a_bullets=[]; particles=[]
score=0; lives=3; wave=1; alive=True; won=False
keys=set()

ROWS_A=4; COLS_A=9; AW=26; AH=18; AGAP=8
ACOLS=[["#ff2d6e"]*COLS_A,["#ff6b2d"]*COLS_A,["#ffb52d"]*COLS_A,["#4d8fff"]*COLS_A]
APTS=[40,30,20,10]

aliens=[]; alien_dir=1; alien_speed=0.7
shoot_t=0; shoot_interval=1.5; anim_t=0

def make_stars():
    return [{"x":random.uniform(0,W),"y":random.uniform(0,H),"s":random.uniform(.3,1.4),"twinkle":random.uniform(0,math.pi*2)} for _ in range(80)]
stars=make_stars()

def make_shields():
    shields=[]
    for si in range(4):
        bx=40+si*(W-80)//3
        for brow in range(3):
            for bcol in range(4):
                shields.append({"x":bx+bcol*8,"y":H-90+brow*8,"w":8,"h":8,"hp":3})
    return shields
shields=make_shields()

def make_aliens():
    global aliens,alien_dir,alien_speed
    aliens=[]
    ox=(W-(COLS_A*(AW+AGAP)-AGAP))//2
    for r in range(ROWS_A):
        for c in range(COLS_A):
            aliens.append({"x":ox+c*(AW+AGAP),"y":55+r*(AH+AGAP),"w":AW,"h":AH,
                           "col":ACOLS[r][c],"pts":APTS[r],"alive":True,"r":r,"frame":0})
    alien_dir=1; alien_speed=0.7+wave*0.18

def add_particles(x,y,col,n=10):
    for _ in range(n):
        a=random.uniform(0,math.pi*2); s=random.uniform(2,5)
        particles.append({"x":x,"y":y,"vx":math.cos(a)*s,"vy":math.sin(a)*s,"life":1.0,"col":col,"r":random.uniform(2,4)})

def shoot_player():
    p_bullets.append({"x":player["x"],"y":player["y"]-player["h"]//2,"vy":-10})

def reset():
    global score,lives,wave,alive,won,p_bullets,a_bullets,particles,shields
    score=0;lives=3;wave=1;alive=True;won=False
    p_bullets=[];a_bullets=[];particles=[]
    player["x"]=W//2
    document.getElementById("s-score").textContent="0"
    document.getElementById("s-lives").textContent="3"
    document.getElementById("s-wave").textContent="1"
    make_aliens(); shields=make_shields()

def draw_alien(a):
    x,y,w,h=a["x"],a["y"],a["w"],a["h"]
    col=a["col"]
    ctx.fillStyle=col
    ctx.shadowColor=col; ctx.shadowBlur=6
    f=a["frame"]  # 0 or 1 for animation
    if a["r"]==0:  # top aliens — crab shape
        ctx.fillRect(x+4,y+2,w-8,h-6)
        ctx.fillRect(x+6,y,w-12,4)
        ctx.fillRect(x,y+4,6,8)
        ctx.fillRect(x+w-6,y+4,6,8)
        ctx.fillRect(x+2 if f==0 else x+4,y+h-5,5,5)
        ctx.fillRect(x+w-7 if f==0 else x+w-9,y+h-5,5,5)
    elif a["r"]==1:  # octopus
        ctx.fillRect(x+2,y+3,w-4,h-6)
        ctx.fillRect(x+4,y,w-8,5)
        ctx.fillRect(x-2,y+3,5,9)
        ctx.fillRect(x+w-3,y+3,5,9)
        ctx.fillRect(x+2 if f==0 else x+6,y+h-5,4,5)
        ctx.fillRect(x+w//2-2,y+h-5,4,5)
        ctx.fillRect(x+w-6 if f==0 else x+w-10,y+h-5,4,5)
    else:  # squid
        ctx.fillRect(x+3,y+3,w-6,h-5)
        ctx.fillRect(x+7,y,w-14,5)
        ctx.fillRect(x,y+4,4,8)
        ctx.fillRect(x+w-4,y+4,4,8)
        ctx.fillRect(x+4 if f==0 else x+1,y+h-4,4,4)
        ctx.fillRect(x+w-8 if f==0 else x+w-5,y+h-4,4,4)
    ctx.shadowBlur=0

def draw_player():
    x,y,w,h=player["x"]-player["w"]//2,player["y"]-player["h"]//2,player["w"],player["h"]
    ctx.fillStyle="#00ee88"; ctx.shadowColor="#00ee88"; ctx.shadowBlur=10
    ctx.fillRect(x+5,y,w-10,h)
    ctx.fillRect(x+w//2-3,y-7,6,9)
    ctx.fillRect(x,y+h-7,w,7)
    ctx.shadowBlur=0

def draw():
    ctx.fillStyle="#04050f"; ctx.fillRect(0,0,W,H)
    # Stars with twinkle
    for s in stars:
        bright=0.3+0.2*math.sin(s["twinkle"])
        ctx.fillStyle=f"rgba(200,215,255,{bright:.2f})"
        ctx.beginPath(); ctx.arc(s["x"],s["y"],s["s"]*.4,0,math.pi*2); ctx.fill()
    # Ground
    ctx.strokeStyle="rgba(0,232,122,.25)"; ctx.lineWidth=1
    ctx.beginPath(); ctx.moveTo(0,H-22); ctx.lineTo(W,H-22); ctx.stroke()
    # Shields
    for sh in shields:
        if sh["hp"]<=0: continue
        alpha=sh["hp"]/3
        ctx.fillStyle=f"rgba(0,200,100,{alpha:.2f})"
        ctx.fillRect(sh["x"],sh["y"],sh["w"],sh["h"])
    # Aliens
    for a in aliens:
        if a["alive"]: draw_alien(a)
    # Player bullets
    ctx.fillStyle="#ffff66"; ctx.shadowColor="#ffff88"; ctx.shadowBlur=7
    for b in p_bullets:
        ctx.beginPath(); ctx.roundRect(b["x"]-2,b["y"]-9,4,14,2); ctx.fill()
    ctx.shadowBlur=0
    # Alien bullets
    ctx.fillStyle="#ff4444"; ctx.shadowColor="#ff6666"; ctx.shadowBlur=6
    for b in a_bullets:
        ctx.beginPath(); ctx.roundRect(b["x"]-2,b["y"]-7,4,11,2); ctx.fill()
    ctx.shadowBlur=0
    # Particles
    for p in particles:
        ctx.globalAlpha=p["life"]; ctx.fillStyle=p["col"]
        ctx.shadowColor=p["col"]; ctx.shadowBlur=5
        ctx.beginPath(); ctx.arc(p["x"],p["y"],p["r"],0,math.pi*2); ctx.fill()
    ctx.globalAlpha=1; ctx.shadowBlur=0
    if alive: draw_player()
    if not alive or won:
        ctx.fillStyle="rgba(2,6,14,.88)"; ctx.fillRect(0,0,W,H)
        col="#ffe050" if won else "#ff2d6e"
        ctx.fillStyle=col; ctx.font="bold 28px monospace"
        ctx.textAlign="center"; ctx.textBaseline="middle"
        ctx.fillText("YOU WIN! 🎉" if won else "GAME OVER",W//2,H//2-20)
        ctx.fillStyle="#7888a8"; ctx.font="13px monospace"
        ctx.fillText(f"Score: {score}",W//2,H//2+8)
        ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
        ctx.fillText("R to restart",W//2,H//2+28)

# Controls
firing=False
def on_key_down(e):
    global firing
    keys.add(e.key)
    if e.key==" ": e.preventDefault(); firing=True
    if e.key=="r" or e.key=="R": reset()
def on_key_up(e):
    global firing
    keys.discard(e.key)
    if e.key==" ": firing=False
document.addEventListener("keydown",create_proxy(on_key_down))
document.addEventListener("keyup",create_proxy(on_key_up))

fire_held=False; left_held=False; right_held=False
def btn_fire_down(e): global fire_held; fire_held=True
def btn_fire_up(e):   global fire_held; fire_held=False
def btn_left_d(e):    global left_held; left_held=True
def btn_left_u(e):    global left_held; left_held=False
def btn_right_d(e):   global right_held; right_held=True
def btn_right_u(e):   global right_held; right_held=False
for bid,fd,fu in [("btn-fire",btn_fire_down,btn_fire_up),("btn-left",btn_left_d,btn_left_u),("btn-right",btn_right_d,btn_right_u)]:
    el=document.getElementById(bid)
    el.addEventListener("touchstart",create_proxy(fd),{"passive":True})
    el.addEventListener("touchend",create_proxy(fu),{"passive":True})
    el.addEventListener("mousedown",create_proxy(fd))
    el.addEventListener("mouseup",create_proxy(fu))

fire_cooldown=0

async def game_loop():
    global alive,won,score,lives,wave,shoot_t,shoot_interval,fire_cooldown
    global alien_dir,alien_speed,p_bullets,a_bullets,anim_t,shields
    import time as tm
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"
    last=tm.time(); anim_frame=0

    while True:
        now=tm.time(); dt=min(now-last,.05); last=now
        anim_t+=dt
        # Star twinkle
        for s in stars:
            s["twinkle"]+=dt*2; s["y"]+=s["s"]*.15
            if s["y"]>H: s["y"]=0; s["x"]=random.uniform(0,W)
        # Particles
        for p in particles: p["x"]+=p["vx"]*dt*60; p["y"]+=p["vy"]*dt*60; p["life"]-=dt*2.5
        particles[:]=[p for p in particles if p["life"]>0]
        # Alien animation frame
        anim_frame+=1
        if anim_frame%45==0:
            for a in aliens:
                if a["alive"]: a["frame"]=1-a["frame"]

        if alive and not won:
            spd=player["speed"]
            if ("ArrowLeft" in keys or left_held) and player["x"]>player["w"]//2+4: player["x"]-=spd
            if ("ArrowRight" in keys or right_held) and player["x"]<W-player["w"]//2-4: player["x"]+=spd
            fire_cooldown-=dt
            if (" " in keys or firing or fire_held) and fire_cooldown<=0:
                shoot_player(); fire_cooldown=0.26
            p_bullets=[b for b in p_bullets if b["y"]>-10]
            for b in p_bullets: b["y"]+=b["vy"]
            a_bullets=[b for b in a_bullets if b["y"]<H+10]
            for b in a_bullets: b["y"]+=b["vy"]
            # Alien movement
            living=[a for a in aliens if a["alive"]]
            if living:
                edge=False
                for a in living:
                    a["x"]+=alien_dir*alien_speed
                    if a["x"]<=4 or a["x"]+a["w"]>=W-4: edge=True
                if edge:
                    alien_dir*=-1
                    for a in living: a["y"]+=12
                    alien_speed=min(alien_speed*1.06,5.0)
                # Shoot
                shoot_t+=dt
                if shoot_t>=shoot_interval:
                    shoot_t=0; shoot_interval=max(0.5,1.5-wave*0.18)
                    # Only bottom aliens per column shoot
                    cols_c={}
                    for a in living:
                        c2=round(a["x"]//(AW+AGAP))
                        if c2 not in cols_c or a["y"]>cols_c[c2]["y"]: cols_c[c2]=a
                    shooter=random.choice(list(cols_c.values()))
                    a_bullets.append({"x":shooter["x"]+shooter["w"]//2,"y":shooter["y"]+shooter["h"],"vy":4.5+wave*.6})
                # Alien reaches bottom
                for a in living:
                    if a["y"]+a["h"]>=H-28: alive=False; break

            # Player bullets hit aliens
            for b in p_bullets[:]:
                hit=False
                for a in aliens:
                    if not a["alive"]: continue
                    if a["x"]-2<=b["x"]<=a["x"]+a["w"]+2 and a["y"]-2<=b["y"]<=a["y"]+a["h"]+2:
                        a["alive"]=False
                        try: p_bullets.remove(b)
                        except: pass
                        score+=a["pts"]; document.getElementById("s-score").textContent=str(score)
                        add_particles(b["x"],b["y"],a["col"])
                        hit=True; break
                if not hit:
                    # Bullet hits shield
                    for sh in shields:
                        if sh["hp"]>0 and sh["x"]<=b["x"]<=sh["x"]+sh["w"] and sh["y"]<=b["y"]<=sh["y"]+sh["h"]:
                            sh["hp"]-=1
                            try: p_bullets.remove(b)
                            except: pass
                            break

            # Alien bullets hit player or shields
            for b in a_bullets[:]:
                hit_shield=False
                for sh in shields:
                    if sh["hp"]>0 and sh["x"]<=b["x"]<=sh["x"]+sh["w"] and sh["y"]<=b["y"]<=sh["y"]+sh["h"]:
                        sh["hp"]-=1
                        try: a_bullets.remove(b)
                        except: pass
                        hit_shield=True; break
                if not hit_shield:
                    if (player["x"]-player["w"]//2<=b["x"]<=player["x"]+player["w"]//2 and
                            player["y"]-player["h"]//2<=b["y"]<=player["y"]+player["h"]//2):
                        try: a_bullets.remove(b)
                        except: pass
                        lives-=1; document.getElementById("s-lives").textContent=str(lives)
                        add_particles(player["x"],player["y"],"#00ee88",14)
                        if lives<=0: alive=False

            if alive and all(not a["alive"] for a in aliens):
                wave+=1; document.getElementById("s-wave").textContent=str(wave)
                if wave>6: won=True
                else: make_aliens(); p_bullets=[]; a_bullets=[]; shields=make_shields()
        draw()
        await asyncio.sleep(1/60)

make_aliens()
asyncio.ensure_future(game_loop())
