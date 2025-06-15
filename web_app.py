#!/usr/bin/env python3
import os
import json
import time
import threading
import requests
from flask import Flask, render_template, jsonify, request

# === LOAD LOOPS ===
ROLE = os.getenv("ROLE", "FLIGHT").upper()
LOOPS_FILE = os.path.join(os.path.dirname(__file__), "LOOPS", f"loops_{ROLE}.txt")
try:
    with open(LOOPS_FILE, "r") as f:
        LOOPS = json.load(f)
except Exception as e:
    print(f"Could not load {LOOPS_FILE}: {e}")
    LOOPS = []

BOTS = [
    {"name": "BOT1", "port": 6001},
    {"name": "BOT2", "port": 6002},
    {"name": "BOT3", "port": 6003},
]

# state: 0=off,1=listening,2=talking
loop_states = {loop["name"]: (0, None) for loop in LOOPS}
user_counts = {loop["name"]: 0 for loop in LOOPS}
loop_configs = {loop["name"]: loop for loop in LOOPS}

bot_pool = {b["name"]: {"port": b["port"], "assigned": None, "last_used": 0} for b in BOTS}

delay_enabled = False
delay_seconds = 3

app = Flask(__name__)

# --- Helper functions ---
def _find_idle_bot():
    idle_bots = [(name, data) for name, data in bot_pool.items() if data["assigned"] is None]
    if not idle_bots:
        return None
    idle_bots.sort(key=lambda x: x[1]["last_used"])
    return idle_bots[0][0]

def _update_bot_assignment(loop_name, new_state):
    loop_cfg = loop_configs[loop_name]
    old_state, old_bot = loop_states[loop_name]
    assigned_bot = old_bot
    post = requests.post

    if loop_cfg["can_listen"] and not loop_cfg["can_talk"]:
        if new_state > 1:
            new_state = 0

    if new_state == 0:
        if old_bot:
            port = bot_pool[old_bot]["port"]
            if delay_enabled and old_state == 2:
                post(f"http://127.0.0.1:{port}/leave_after_delay")
            else:
                post(f"http://127.0.0.1:{port}/leave")
                post(f"http://127.0.0.1:{port}/mute")
            bot_pool[old_bot]["assigned"] = None
            bot_pool[old_bot]["last_used"] = time.time()
        loop_states[loop_name] = (0, None)
        return

    if not assigned_bot:
        assigned_bot = _find_idle_bot()
        if not assigned_bot:
            return
        bot_pool[assigned_bot]["assigned"] = loop_name
    port = bot_pool[assigned_bot]["port"]

    if new_state == 2:
        for other_loop in LOOPS:
            other_name = other_loop["name"]
            if other_name == loop_name:
                continue
            ostate, obot = loop_states[other_name]
            if ostate == 2 and obot:
                oport = bot_pool[obot]["port"]
                if delay_enabled:
                    post(f"http://127.0.0.1:{oport}/mute_after_delay")
                else:
                    post(f"http://127.0.0.1:{oport}/mute")
                loop_states[other_name] = (1, obot)
                bot_pool[obot]["last_used"] = time.time()
        post(f"http://127.0.0.1:{port}/join", json={"loop": loop_name})
        if delay_enabled:
            threading.Timer(delay_seconds, lambda: post(f"http://127.0.0.1:{port}/talk")).start()
        else:
            post(f"http://127.0.0.1:{port}/talk")
    elif new_state == 1:
        if old_state == 2 and delay_enabled:
            post(f"http://127.0.0.1:{port}/mute_after_delay")
        else:
            post(f"http://127.0.0.1:{port}/join", json={"loop": loop_name})
            post(f"http://127.0.0.1:{port}/mute")

    bot_pool[assigned_bot]["assigned"] = loop_name
    bot_pool[assigned_bot]["last_used"] = time.time()
    loop_states[loop_name] = (new_state, assigned_bot)

def _poll_status():
    for bot_name, bot in bot_pool.items():
        try:
            r = requests.get(f"http://127.0.0.1:{bot['port']}/status", timeout=0.5)
            info = r.json()
            if "user_counts" in info:
                for loop in LOOPS:
                    name = loop["name"]
                    user_counts[name] = info["user_counts"].get(name, 0)
        except Exception:
            pass

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html', loops=LOOPS)

@app.route('/api/status')
def api_status():
    _poll_status()
    data = {}
    for loop in LOOPS:
        name = loop["name"]
        state, _ = loop_states[name]
        data[name] = {"state": state, "count": user_counts.get(name, 0)}
    return jsonify({"loops": data, "delay": delay_enabled})

@app.route('/api/toggle', methods=['POST'])
def api_toggle():
    name = request.json.get('loop')
    if name not in loop_states:
        return jsonify(ok=False), 400
    cfg = loop_configs[name]
    state, _ = loop_states[name]
    if not cfg["can_listen"]:
        return jsonify(ok=False)
    if state == 0:
        new_state = 1
    elif state == 1:
        new_state = 2 if cfg.get("can_talk", False) else 1
    else:
        new_state = 1
    _update_bot_assignment(name, new_state)
    return jsonify(ok=True)

@app.route('/api/off', methods=['POST'])
def api_off():
    name = request.json.get('loop')
    if name in loop_states:
        _update_bot_assignment(name, 0)
    return jsonify(ok=True)

@app.route('/api/delay', methods=['POST'])
def api_delay():
    global delay_enabled
    delay_enabled = not delay_enabled
    for bot in bot_pool.values():
        try:
            if delay_enabled:
                requests.post(f"http://127.0.0.1:{bot['port']}/delay_on", json={"seconds": delay_seconds})
            else:
                requests.post(f"http://127.0.0.1:{bot['port']}/delay_off")
        except Exception:
            pass
    return jsonify(delay=delay_enabled)

if __name__ == '__main__':
    app.run(debug=True)
