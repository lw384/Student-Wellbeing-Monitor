# src/wellbeing_system/ui/app.py
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Flask wellbeing web is running!"


def run_app():
    app.run(debug=True)
