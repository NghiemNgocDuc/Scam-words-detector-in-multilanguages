import time
import os
import tempfile
import unicodedata
from flask import Flask, render_template, request, jsonify
from collections import deque

# bring in your existing score_text() from risk_service.py
from risk_service import score_text

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():

    data = request.get_json()
    text = data.get('text', '').strip()
    lang = data.get('lang', 'vi')

    score, reasons = score_text(text, lang)

    if score >= 60:
        label = "Scam"
    elif score >= 30:
        label = "Caution"
    else:
        label = "Safe"

    return jsonify({
        "text": text,
        "score": score,
        "label": label,
        "reasons": reasons
    })

if __name__ == "__main__":
    # No audio thread here, just serve Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
