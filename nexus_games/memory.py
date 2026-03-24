import asyncio, random, math, time
from js import document
from pyodide.ffi import create_proxy

canvas=document.getElementById("gameCanvas")
ctx=canvas.getContext("2d")
W,H=380,380
COLS=ROWS=4; GAP=10
CELL=(W-GAP*(COLS+1))//COLS

SYMBOLS=["★","♦","♠","♣","♥","⬟","◉","▲"]
SYM_COLS=["#00f0ff","#ff2d6e","#ffe066","#bf5fff","#00ff88","#ff8c00","#4d8fff","#ff6688"]

cards=[]
flipped=[]
matched=0; moves=0; best=None; locked=False; lock_t=None
particles=[]

def add_match_particles(cx,cy,col):
    for _ in range(14):
        a=random.uniform(0,math.pi*2); s=random.uniform(2,6)
        particles.append({"x":cx,"y":cy,"vx":math.cos(a)*s,"vy":math.sin(a)*s,"life":1.2,"col":col})

class Card:
    def __init__(self,idx,sym,col):
        self.idx=idx; self.sym=sym; self.col=col
        self.face_up=False; self.matched=False
        self.flip_prog=0.0
        self.flipping=False; self.flip_dir=1
        self.shake=0.0  # for wrong match shake
        self.match_scale=1.0  # for match pop
    def rect(self):
        r=self.idx//COLS; c=self.idx%COLS
        return GAP+c*(CELL+GAP), GAP+r*(CELL+GAP), CELL, CELL
    def start_flip(self,to_front):
        self.flipping=True; self.flip_dir=1 if to_front else -1
    def start_shake(self):
        self.shake=0.3
    def start_match(self):
        self.match_scale=1.3
    def update(self,dt):
        if self.flipping:
            self.flip_prog+=self.flip_dir*dt*5
            if self.flip_prog>=1.0: self.flip_prog=1.0; self.flipping=False
            elif self.flip_prog<=0.0: self.flip_prog=0.0; self.flipping=False
        if self.shake>0:
            self.shake-=dt*3
            if self.shake<0: self.shake=0
        if self.match_scale>1.0:
            self.match_scale-=dt*3
            if self.match_scale<1.0: self.match_scale=1.0
    def draw(self,ct):
        bx,by,cw,ch=self.rect()
        # Shake offset
        sx=math.sin(self.shake*30)*4*self.shake if self.shake>0 else 0
        bx+=int(sx)
        scale=abs(math.cos(self.flip_prog*math.pi/2)) if 0<self.flip_prog<1 else 1.0
        showing_front=self.flip_prog>=0.5
        # Match scale
        ms=self.match_scale
        sw=max(2,int(cw*scale*ms)); sh=int(ch*ms)
        ox=(cw-sw)//2; oy=(ch-sh)//2
        if self.matched:
            ct.fillStyle="#082818"
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.fill()
            ct.strokeStyle=self.col; ct.lineWidth=2
            ct.shadowColor=self.col; ct.shadowBlur=10
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.stroke()
            ct.shadowBlur=0
            if sw>20:
                ct.fillStyle=self.col; ct.font=f"{int(sh*.48)}px serif"
                ct.textAlign="center"; ct.textBaseline="middle"
                ct.fillText(self.sym,bx+cw//2,by+ch//2)
        elif showing_front:
            ct.fillStyle="#121e50"
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.fill()
            ct.strokeStyle=self.col; ct.lineWidth=2
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.stroke()
            # Highlight
            ct.fillStyle="rgba(255,255,255,.06)"
            ct.beginPath(); ct.roundRect(bx+ox+2,by+oy+2,sw-4,min(10,sh//3-2),3); ct.fill()
            if sw>20:
                ct.fillStyle=self.col
                ct.shadowColor=self.col; ct.shadowBlur=8
                ct.font=f"{int(sh*.48)}px serif"
                ct.textAlign="center"; ct.textBaseline="middle"
                ct.fillText(self.sym,bx+cw//2,by+ch//2)
                ct.shadowBlur=0
        else:
            ct.fillStyle="#0e1630"
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.fill()
            ct.strokeStyle="#1e2e60"; ct.lineWidth=1.5
            ct.beginPath(); ct.roundRect(bx+ox,by+oy,sw,sh,8); ct.stroke()
            if sw>24:
                ct.fillStyle="#2e4080"; ct.font=f"{int(sh*.36)}px monospace"
                ct.textAlign="center"; ct.textBaseline="middle"
                ct.fillText("?",bx+cw//2,by+ch//2)

def init_cards():
    global cards,flipped,matched,moves,locked,lock_t,particles
    deck=SYMBOLS*2; random.shuffle(deck)
    cards=[Card(i,deck[i],SYM_COLS[SYMBOLS.index(deck[i])]) for i in range(16)]
    flipped=[]; matched=0; moves=0; locked=False; lock_t=None; particles=[]
    document.getElementById("s-pairs").textContent="0/8"
    document.getElementById("s-moves").textContent="0"

def on_card_click(idx):
    global flipped,matched,moves,locked,lock_t,best
    if locked or cards[idx].face_up or cards[idx].matched: return
    cards[idx].face_up=True; cards[idx].start_flip(True)
    flipped.append(idx)
    if len(flipped)==2:
        moves+=1; document.getElementById("s-moves").textContent=str(moves)
        a,b=flipped
        if cards[a].sym==cards[b].sym:
            cards[a].matched=cards[b].matched=True
            bx,by,cw,ch=cards[a].rect()
            add_match_particles(bx+cw//2,by+ch//2,cards[a].col)
            bx2,by2,cw2,ch2=cards[b].rect()
            add_match_particles(bx2+cw2//2,by2+ch2//2,cards[b].col)
            cards[a].start_match(); cards[b].start_match()
            matched+=1; flipped=[]
            document.getElementById("s-pairs").textContent=f"{matched}/8"
            if matched==8:
                if best is None or moves<best:
                    best=moves
                    document.getElementById("s-best").textContent=str(best)
        else:
            cards[a].start_shake(); cards[b].start_shake()
            locked=True; lock_t=time.time()

def handle_click(mx,my):
    for i,card in enumerate(cards):
        bx,by,cw,ch=card.rect()
        if bx<=mx<=bx+cw and by<=my<=by+ch:
            on_card_click(i); break

def on_click(e):
    rect=canvas.getBoundingClientRect()
    handle_click(e.clientX-rect.left, e.clientY-rect.top)
def on_touch(e):
    e.preventDefault()
    t=e.changedTouches.item(0); rect=canvas.getBoundingClientRect()
    handle_click(t.clientX-rect.left, t.clientY-rect.top)

canvas.addEventListener("click",create_proxy(on_click))
canvas.addEventListener("touchend",create_proxy(on_touch))
document.getElementById("reset-btn").addEventListener("click",create_proxy(lambda e:init_cards()))

async def game_loop():
    global locked,lock_t,flipped
    import time as tm
    loading=document.getElementById("loading")
    loading.classList.add("hidden")
    await asyncio.sleep(.55)
    loading.style.display="none"
    last=tm.time()
    while True:
        now=tm.time(); dt=now-last; last=now
        if locked and lock_t and now-lock_t>0.9:
            for i in flipped:
                cards[i].face_up=False; cards[i].start_flip(False)
            flipped=[]; locked=False; lock_t=None
        for card in cards: card.update(dt)
        # Particles
        for p in particles: p["x"]+=p["vx"]*dt*60; p["y"]+=p["vy"]*dt*60; p["life"]-=dt*2.5
        particles[:]=[p for p in particles if p["life"]>0]
        # Draw
        ctx.fillStyle="#030610"; ctx.fillRect(0,0,W,H)
        # Board bg
        ctx.fillStyle="#080f22"
        ctx.beginPath(); ctx.roundRect(GAP//2,GAP//2,W-GAP,H-GAP,12); ctx.fill()
        for card in cards: card.draw(ctx)
        # Particles
        for p in particles:
            ctx.globalAlpha=p["life"]; ctx.fillStyle=p["col"]
            ctx.shadowColor=p["col"]; ctx.shadowBlur=5
            ctx.beginPath(); ctx.arc(p["x"],p["y"],3,0,math.pi*2); ctx.fill()
        ctx.globalAlpha=1; ctx.shadowBlur=0
        if matched==8:
            ctx.fillStyle="rgba(2,6,14,.86)"; ctx.fillRect(0,0,W,H)
            ctx.fillStyle="#ffe050"; ctx.font="bold 28px monospace"
            ctx.textAlign="center"; ctx.textBaseline="middle"
            ctx.fillText("ALL MATCHED! 🎉",W//2,H//2-22)
            ctx.fillStyle="#7888a8"; ctx.font="14px monospace"
            ctx.fillText(f"{moves} moves",W//2,H//2+8)
            if best is not None:
                ctx.fillStyle="#4a5878"; ctx.font="12px monospace"
                ctx.fillText(f"Best: {best} moves",W//2,H//2+28)
        await asyncio.sleep(1/60)

init_cards()
asyncio.ensure_future(game_loop())
