import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

NPOINT_URL = "https://api.npoint.io/e52209239c5687bad3a9"
ADMIN_PASSWORD = "TheDeven@2026!"

def get_bookings():
    try:
        r = requests.get(NPOINT_URL, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else []
    except:
        pass
    return []

def save_bookings(data):
    try:
        requests.post(NPOINT_URL, json=data, timeout=15)
    except:
        pass

@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>The Deven Live ✅</h1><p>Template error: {e}</p><p>Folder 'templates' check karo</p>"

@app.route('/admin')
def admin():
    try:
        return render_template('admin.html')
    except Exception as e:
        return f"<h1>Admin Live ✅</h1><p>Error: {e}</p>"

@app.route('/api/bookings', methods=['GET'])
def api_get():
    return jsonify(get_bookings())

@app.route('/api/book', methods=['POST'])
def api_book():
    bookings = get_bookings()
    bookings.append(request.get_json())
    save_bookings(bookings)
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def api_login():
    if request.get_json().get('password') == ADMIN_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/delete', methods=['POST'])
def api_delete():
    try:
        idx = int(request.get_json().get('index', -1))
        bookings = get_bookings()
        bookings.pop(idx)
        save_bookings(bookings)
        return jsonify({"success": True})
    except:
        return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
