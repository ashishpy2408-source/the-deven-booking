"""
The Deven — Studio Booking (Fixed - Price Removed + Slot System Fixed)
"""
import os
import sqlite3
import secrets
from datetime import datetime, date, timedelta, time as dtime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash

STUDIO_NAME = "The Deven"
STUDIO_TAGLINE = "A daylight studio for photo, film, and sound."
STUDIO_LOCATION = "Raipur, Chhattisgarh"
DEFAULT_SESSION_MINUTES = 60
OPEN_HOUR = 9
CLOSE_HOUR = 20
BOOKABLE_DAYS_AHEAD = 60
CLOSED_WEEKDAYS = set()
ALLOWED_DURATIONS = [60, 120, 180, 300, 600]

# PRICE KHALI RAKHA HAI - ERROR NAHI AYEGA, DIKHEGA BHI NAHI
RESOURCES = {
    "daylight_studio": {"name": "Daylight Studio", "icon": "📸", "price": "", "desc": "Photo/Film/Sound"},
    "meeting_room": {"name": "Meeting Room", "icon": "💼", "price": "", "desc": "Meetings/Podcast"}
}

ADMIN_PASSWORD = os.environ.get("DEVEN_ADMIN_PASSWORD", "changeme123")
SECRET_KEY = os.environ.get("DEVEN_SECRET_KEY", secrets.token_hex(32))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "the_deven.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TEXT NOT NULL,
            resource TEXT DEFAULT 'daylight_studio'
        )
    """)
    try:
        db.execute("ALTER TABLE bookings ADD COLUMN resource TEXT DEFAULT 'daylight_studio'")
    except:
        pass
    db.execute("""
        CREATE TABLE IF NOT EXISTS blocked_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            resource TEXT DEFAULT 'daylight_studio'
        )
    """)
    try:
        db.execute("ALTER TABLE blocked_slots ADD COLUMN resource TEXT DEFAULT 'daylight_studio'")
    except:
        pass
    db.commit()
    db.close()

def get_gallery_images():
    gallery = {"studio": [], "meeting": [], "rules": []}
    try:
        base = os.path.join(app.static_folder, "images")
        for key in gallery.keys():
            folder = os.path.join(base, key)
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    if f.lower().endswith(('.png','.jpg','.jpeg','.webp')):
                        gallery[key].append(f"images/{key}/{f}")
    except:
        pass
    return gallery

with app.app_context():
    init_db()

def generate_day_slots(duration_minutes=60):
    slots = []
    step = timedelta(minutes=60)
    dur = timedelta(minutes=duration_minutes)
    today_anchor = datetime.combine(date.today(), dtime(OPEN_HOUR, 0))
    end_anchor = datetime.combine(date.today(), dtime(CLOSE_HOUR, 0))
    cur = today_anchor
    while cur + dur <= end_anchor:
        slots.append((cur.strftime("%H:%M"), (cur + dur).strftime("%H:%M")))
        cur += step
    return slots

def get_taken_ranges(db, day_str, resource):
    taken = []
    rows = db.execute("SELECT start_time, end_time FROM bookings WHERE date =? AND status='confirmed' AND resource=?", (day_str, resource)).fetchall()
    taken.extend((r["start_time"], r["end_time"]) for r in rows)
    rows = db.execute("SELECT start_time, end_time FROM blocked_slots WHERE date =? AND resource=?", (day_str, resource)).fetchall()
    taken.extend((r["start_time"], r["end_time"]) for r in rows)
    return taken

def ranges_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def is_day_bookable(day: date):
    if day < date.today(): return False
    if day > date.today() + timedelta(days=BOOKABLE_DAYS_AHEAD): return False
    if day.weekday() in CLOSED_WEEKDAYS: return False
    return True

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_owner"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def book_page():
    return render_template("book.html",
        studio_name=STUDIO_NAME, tagline=STUDIO_TAGLINE, location=STUDIO_LOCATION,
        session_length=DEFAULT_SESSION_MINUTES, days_ahead=BOOKABLE_DAYS_AHEAD,
        resources=RESOURCES, gallery=get_gallery_images())

@app.route("/rules")
def rules_page():
    return render_template("rules.html",
        studio_name=STUDIO_NAME, location=STUDIO_LOCATION,
        gallery=get_gallery_images())

@app.route("/api/availability")
def api_availability():
    try:
        day_str = request.args.get("date", "")
        duration = request.args.get("duration", str(DEFAULT_SESSION_MINUTES))
        resource = request.args.get("resource", "daylight_studio")
        if resource not in RESOURCES: resource = "daylight_studio"
        try:
            duration = int(duration)
            if duration not in ALLOWED_DURATIONS: duration = 60
        except:
            duration = DEFAULT_SESSION_MINUTES
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"date": day_str, "bookable": False, "slots": [], "error": "invalid date"}), 200
        if not is_day_bookable(day):
            return jsonify({"date": day_str, "bookable": False, "slots": []})
        db = get_db()
        taken = get_taken_ranges(db, day_str, resource)
        all_slots = generate_day_slots(duration)
        is_today = day == date.today()
        now_str = datetime.now().strftime("%H:%M")
        out = []
        for start_s, end_s in all_slots:
            taken_flag = any(ranges_overlap(start_s, end_s, t0, t1) for t0, t1 in taken)
            past_flag = is_today and start_s <= now_str
            out.append({"start": start_s, "end": end_s, "available": not taken_flag and not past_flag})
        return jsonify({"date": day_str, "bookable": True, "duration": duration, "resource": resource, "slots": out})
    except Exception as e:
        print(f"Availability error: {e}")
        return jsonify({"date": day_str if 'day_str' in locals() else '', "bookable": False, "slots": [], "error": str(e)}), 200

@app.route("/api/slots")
def api_slots_alias():
    return api_availability()

@app.route("/api/book", methods=["POST"])
def api_book():
    data = request.get_json(silent=True) or {}
    day_str = (data.get("date") or "").strip()
    start_s = (data.get("start") or data.get("start_time") or "").strip()
    duration = data.get("duration")
    resource = (data.get("resource") or data.get("space") or "daylight_studio").strip()
    if resource in ["daylight", "studio"]: resource = "daylight_studio"
    if resource == "meeting": resource = "meeting_room"
    if resource not in RESOURCES: resource = "daylight_studio"
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "noemail@example.com").strip()
    phone = (data.get("phone") or "").strip()
    notes = (data.get("notes") or "").strip()
    if not all([day_str, start_s, name]):
        return jsonify({"error": "Missing required fields."}), 400
    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date."}), 400
    if not is_day_bookable(day):
        return jsonify({"error": "That date isn't available."}), 400
    try:
        duration = int(duration) if duration else 60
        if duration not in ALLOWED_DURATIONS: duration = 60
    except:
        duration = 60
    try:
        sh, sm = map(int, start_s.split(':'))
        start_dt = datetime.combine(day, dtime(sh, sm))
        end_dt = start_dt + timedelta(minutes=duration)
        if end_dt.time() > dtime(CLOSE_HOUR, 0):
            return jsonify({"error": f"Studio closes at {CLOSE_HOUR}:00"}), 400
        final_end_s = end_dt.strftime("%H:%M")
    except:
        return jsonify({"error": "Invalid start time."}), 400
    db = get_db()
    taken = get_taken_ranges(db, day_str, resource)
    if any(ranges_overlap(start_s, final_end_s, t0, t1) for t0, t1 in taken):
        return jsonify({"error": f"{RESOURCES[resource]['name']} already booked for that time."}), 409
    db.execute("""INSERT INTO bookings (date, start_time, end_time, name, email, phone, notes, status, created_at, resource)
           VALUES (?,?,?,?,?,?,?, 'confirmed',?,?)""",
        (day_str, start_s, final_end_s, name, email, phone, notes, datetime.utcnow().isoformat(), resource))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if secrets.compare_digest(pw, ADMIN_PASSWORD):
            session["is_owner"] = True
            next_url = request.args.get("next") or url_for("admin_dashboard")
            return redirect(next_url)
        error = "Incorrect password."
    return render_template("admin_login.html", studio_name=STUDIO_NAME, error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_owner", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    today_str = date.today().isoformat()
    upcoming = db.execute("SELECT * FROM bookings WHERE date >=? AND status='confirmed' ORDER BY date ASC, start_time ASC", (today_str,)).fetchall()
    past = db.execute("SELECT * FROM bookings WHERE date <? AND status='confirmed' ORDER BY date DESC, start_time DESC LIMIT 50", (today_str,)).fetchall()
    cancelled = db.execute("SELECT * FROM bookings WHERE status='cancelled' ORDER BY date DESC LIMIT 50").fetchall()
    blocked = db.execute("SELECT * FROM blocked_slots WHERE date >=? ORDER BY date ASC", (today_str,)).fetchall()
    return render_template("admin.html", studio_name=STUDIO_NAME, upcoming=upcoming, past=past, cancelled=cancelled, blocked=blocked, booking_link=request.host_url.rstrip("/") + url_for("book_page"), resources=RESOURCES)

@app.route("/admin/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def admin_cancel_booking(booking_id):
    db = get_db()
    db.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
    db.commit()
    flash("Cancelled.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/booking/<int:booking_id>/delete", methods=["POST"])
@login_required
def admin_delete_booking(booking_id):
    db = get_db()
    db.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    db.commit()
    flash("Deleted.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/block", methods=["POST"])
@login_required
def admin_block_slot():
    day_str = request.form.get("date", "").strip()
    start_s = request.form.get("start", "").strip()
    end_s = request.form.get("end", "").strip()
    reason = request.form.get("reason", "").strip()
    resource = request.form.get("resource", "daylight_studio").strip()
    if resource not in RESOURCES: resource="daylight_studio"
    if day_str and start_s and end_s:
        db = get_db()
        db.execute("INSERT INTO blocked_slots (date, start_time, end_time, reason, created_at, resource) VALUES (?,?,?,?,?,?)",
            (day_str, start_s, end_s, reason, datetime.utcnow().isoformat(), resource))
        db.commit()
        flash("Blocked.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/block/<int:block_id>/delete", methods=["POST"])
@login_required
def admin_unblock_slot(block_id):
    db = get_db()
    db.execute("DELETE FROM blocked_slots WHERE id=?", (block_id,))
    db.commit()
    flash("Unblocked.")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
