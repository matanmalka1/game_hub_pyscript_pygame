import asyncio, random
import numpy as np
from js import document
from pyodide.ffi import create_proxy

from tictactoe_core import (
    TicTacToeNN, train_step, generate_dataset, trained_models, LEVEL_NOISE
)
from js import window, Uint8Array, URL
import json

export_weights = None


async def do_train(e):
    global export_weights
    level  = document.getElementById("train-level").value
    epochs = int(document.getElementById("train-epochs").value)
    noise  = LEVEL_NOISE[level]
    log_el = document.getElementById("train-log")
    bar    = document.getElementById("train-progress-bar")
    btn    = document.getElementById("train-btn")
    exp_btn= document.getElementById("export-btn")

    btn.disabled = True; exp_btn.style.display = "none"
    log_el.textContent = f"Generating {level} dataset..."
    await asyncio.sleep(0.05)

    X, Y = generate_dataset(noise, n_games=400)
    model = TicTacToeNN(hidden=64)
    log_el.textContent = f"Training {level} — {len(X)} samples, {epochs} epochs\n"

    batch = 128
    lr    = 0.005
    for ep in range(epochs):
        idx = np.random.permutation(len(X))
        X, Y = X[idx], Y[idx]
        loss = 0.0
        for i in range(0, len(X), batch):
            loss = train_step(model, X[i:i+batch], Y[i:i+batch], lr)
        if (ep+1) % (epochs//10 or 1) == 0:
            pct = (ep+1)/epochs*100
            bar.style.width = f"{pct}%"
            log_el.textContent += f"Epoch {ep+1}/{epochs}  loss={loss:.4f}\n"
            log_el.scrollTop = log_el.scrollHeight
            await asyncio.sleep(0.01)

    trained_models[level] = model
    export_weights = model.save_weights()
    log_el.textContent += f"\n✅ {level.upper()} model trained! Now active for this level.\n"
    btn.disabled = False
    exp_btn.style.display = "inline-block"
    bar.style.width = "100%"


def on_export(e):
    if not export_weights: return
    level = document.getElementById("train-level").value
    packed = {k: v.tolist() for k, v in export_weights.items()}
    blob_str = json.dumps(packed)
    blob_data = blob_str.encode()
    arr = Uint8Array.new(len(blob_data))
    for i, b2 in enumerate(blob_data): arr[i] = b2
    blob = window.Blob.new([arr], {"type": "application/json"})
    url  = URL.createObjectURL(blob)
    a    = document.createElement("a")
    a.href = url; a.download = f"model_{level}.json"
    a.click()
    URL.revokeObjectURL(url)


document.getElementById("train-btn").addEventListener("click", create_proxy(do_train))
document.getElementById("export-btn").addEventListener("click", create_proxy(on_export))
