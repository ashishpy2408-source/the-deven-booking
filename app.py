import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# NAYA DATABASE - FINAL
NPOINT_URL = "https://api.npoint.io/e52209239c5687bad3a9"
ADMIN_PASSWORD = "TheDeven@2026!"

def get_bookings():
    try:
        r = requests.get(NPOINT_URL, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
        return []
    except:
        return []

def save_bookings(bookings):
    try:
        requests.post(NPOINT_URL, json=bookings, timeout=10)
        return True
    except:
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/bookings', methods=['GET'])
def api_get():
    return jsonify(get_bookings())

@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.json
    bookings = get_bookings()
    bookings.append(data)
    save_bookings(bookings)
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
