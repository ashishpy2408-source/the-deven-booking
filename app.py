import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# FINAL PERMANENT DATABASE - kabhi change mat karna
NPOINT_URL = "https://api.npoint.io/e52209239c5687bad3a9"
ADMIN_PASSWORD = "TheDeven@2026!"

def get_bookings():
    try:
        r = requests.get(NPOINT_URL, timeout=15)
        return r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
    except:
        return []

def save_bookings(data):
    try:
        requests.post(NPOINT_URL, json=data, timeout=15)
    except:
        pass

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
    bookings = get_bookings()
    bookings.append(request.json)
    save_bookings(bookings)
    return jsonify({"success": True})

@app.route('/api/login', methods=['POST'])
def api_login():
    if request.json.get('password') == ADMIN_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/delete', methods=['POST'])
def api_delete():
    try:
        idx = int(request.json.get('index', -1))
        bookings = get_bookings()
        bookings.pop(idx)
        save_bookings(bookings)
        return jsonify({"success": True})
    except:
        return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
