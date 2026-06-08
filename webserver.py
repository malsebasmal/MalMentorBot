from threading import Thread

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    server = Thread(target=run)
    server.start()
