import threading
from flask import Flask
import config

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Server is Online & Healthy!"

def run_flask():
    app.run(host="0.0.0.0", port=config.PORT)

def keep_alive():
    """ Render Web Service တွင် Port bind လုပ်ပြီး မအိပ်သွားစေရန် ပြုလုပ်သည့် Service """
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
