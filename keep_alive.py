from flask import Flask, request
from threading import Thread
import os, time

app = Flask(__name__)

@app.get("/")
def home():
    print(f"[KEEPALIVE] {time.strftime('%H:%M:%S')} {request.remote_addr} GET /")
    return "Bot en ligne ✅", 200

def run():
    port = int(os.getenv("PORT", "8080"))  # <-- Render fournit PORT
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
