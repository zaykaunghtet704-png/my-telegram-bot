import time
import threading
from datetime import datetime
from flask import Flask
from database import db

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Core Service Active"

def start_flask(port):
    app.run(host='0.0.0.0', port=port)

def start_night_mode_scheduler(bot):
    def scheduler_loop():
        while True:
            try:
                now = datetime.now().strftime("%H:%M")
                db.cursor.execute("SELECT chat_id, night_start, night_end FROM group_settings WHERE night=1")
                rows = db.cursor.fetchall()
                for cid, n_start, n_end in rows:
                    if now == n_start:
                        try: bot.send_message(cid, "🌙 **Night Mode Active:** Chatting restricted.")
                        except Exception: pass
                    elif now == n_end:
                        try: bot.send_message(cid, "☀️ **Night Mode Deactivated:** Chat opened.")
                        except Exception: pass
            except Exception: pass
            time.sleep(60)

    threading.Thread(target=scheduler_loop, daemon=True).start()
