"""
The Deven — Studio Booking (Flexible Duration Edition)

Client decides session length: 1h / 2h / 3h / Half Day / Full Day
"""

import os
import sqlite3
import secrets
from datetime import datetime, date, timedelta, time as dtime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, g, flash
)

# ---------------------------------------------------------------------------
# CONFIG — edit these to fit your studio
# ---------------------------------------------------------------------------
STUDIO_NAME = "The Deven"
STUDIO_TAGLINE = "A daylight studio for photo, film, and sound."
STUDIO_LOCATION = "Raipur, Chhattisgarh"
DEFAULT_SESSION_MINUTES = 60      # default if client doesn't choose
OPEN_HOUR = 9                    # studio opens, 24h clock
CLOSE_HOUR = 20                  # last slot must END by this hour
BOOKABLE_DAYS_AHEAD = 60         # how far into the future people can book
CLOSED_WEEKDAYS = set()          # 0=Mon ... 6=Sun, e.g. {6} to close Sundays

# Allowed durations client can choose (minutes)
ALLOWED_DURATIONS = [60, 120, 180, 300, 600]

ADMIN_PASSWORD = os.environ.get("DEVEN_ADMIN_PASSWORD", "changeme123")
SECRET_KEY = os.environ.get("DEVEN_SECRET_KEY", secrets.token_hex(32))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "the_deven.db")

# ---------------------------------------------------------------------------
# App + DB setup
# ---------------------------------------------------------------------------
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
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS blocked_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# ---------------------------------------------------------------------------
# Slot helpers — NOW FLEXIBLE
# ---------------------------------------------------------------------------
def generate_day_slots(duration_minutes=60):
    """All possible slot (start,end) for one day that can FIT duration_minutes."""
    slots = []
    step = timedelta(minutes=60)  # start every hour
    dur = timedelta(minutes=duration_minutes)
    today_anchor = datetime.combine(date.today(), dtime(OPEN_HOUR, 0))
    end_anchor = datetime.combine(date.today(), dtime(CLOSE_HOUR, 0))
    
    cur = today_anchor
    while cur + dur <= end_anchor:
        start_s = cur.strftime("%H:%M")
        end_s = (cur + dur).strftime("%H:%M")
        slots.append((start_s, end_s))
        cur += step
    return slots

def get_taken_ranges(db, day_str):
    """Return list of (start,end) strings already booked or blocked on day_str."""
    taken = []
    rows = db.execute(
        "SELECT start_time, end_time FROM bookings WHERE date = ? AND status = 'confirmed'",
        (day_str,),
    ).fetchall()
    taken.extend((r["start_time"], r["end_time"]) for r in rows)
    rows = db.execute(
        "SELECT start_time, end_time FROM blocked_slots WHERE date = ?",
        (day_str,),
    ).fetchall()
    taken.extend((r["start_time"], r["end_time"]) for r in rows)
    return taken

def ranges_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def is_day_bookable(day: date):
    if day < date.today():
        return False
    if day > date.today() + timedelta(days=BOOKABLE_DAYS_AHEAD):
        return False
    if day.weekday() in CLOSED_WEEKDAYS:
        return False
    return True

# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_owner"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def book_page():
    return render_template(
        "book.html",
        studio_name=STUDIO_NAME,
        tagline=STUDIO_TAGLINE,
        location=STUDIO_LOCATION,
        session_length=DEFAULT_SESSION_MINUTES,
        days_ahead=BOOKABLE_DAYS_AHEAD,
    )

@app.route("/api/availability")
def api_availability():
    day_str = request.args.get("date", "")
    duration = request.args.get("duration", str(DEFAULT_SESSION_MINUTES))
    try:
        duration = int(duration)
        if duration not in ALLOWED_DURATIONS:
            # allow any but clamp to allowed list closest
            if duration < 60:
                duration = 60
    except:
        duration = DEFAULT_SESSION_MINUTES

    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    if not is_day_bookable(day):
        return jsonify({"date": day_str, "bookable": False, "slots": []})

    db = get_db()
    taken = get_taken_ranges(db, day_str)
    all_slots = generate_day_slots(duration)

    is_today = day == date.today()
    now_str = datetime.now().strftime("%H:%M")

    out = []
    for start_s, end_s in all_slots:
        taken_flag = any(ranges_overlap(start_s, end_s, t0, t1) for t0, t1 in taken)
        past_flag = is_today and start_s <= now_str
        out.append({
            "start": start_s,
            "end": end_s,
            "available": not taken_flag and not past_flag,
        })

    return jsonify({"date": day_str, "bookable": True, "duration": duration, "slots": out})

@app.route("/api/book", methods=["POST"])
def api_book():
    data = request.get_json(silent=True) or {}
    day_str = (data.get("date") or "").strip()
    start_s = (data.get("start") or "").strip()
    end_s = (data.get("end") or "").strip()
    duration = data.get("duration")
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not all([day_str, start_s, name, email]):
        return jsonify({"error": "Missing required fields."}), 400

    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date."}), 400

    if not is_day_bookable(day):
        return jsonify({"error": "That date isn't available for booking."}), 400

    # Determine duration
    try:
        duration = int(duration) if duration else 60
        if duration not in ALLOWED_DURATIONS:
            duration = 60
    except:
        duration = 60

    # Recalculate end based on duration to avoid tampering
    try:
        sh, sm = map(int, start_s.split(':'))
        start_dt = datetime.combine(day, dtime(sh, sm))
        end_dt = start_dt + timedelta(minutes=duration)
        if end_dt.time() > dtime(CLOSE_HOUR, 0):
            return jsonify({"error": f"Studio closes at {CLOSE_HOUR}:00, this {duration} min session would go beyond."}), 400
        calc_end_s = end_dt.strftime("%H:%M")
    except:
        return jsonify({"error": "Invalid start time."}), 400

    # If client sent end_s, use calculated one (more secure)
    final_end_s = calc_end_s

    # Validate that start is a valid hourly start
    valid_starts = [s for s, e in generate_day_slots(duration)]
    if start_s not in valid_starts:
        # also allow any hour between OPEN and CLOSE that fits
        try:
            if not (OPEN_HOUR <= sh < CLOSE_HOUR):
                return jsonify({"error": "That isn't a valid time slot."}), 400
        except:
            return jsonify({"error": "That isn't a valid time slot."}), 400

    db = get_db()
    taken = get_taken_ranges(db, day_str)
    if any(ranges_overlap(start_s, final_end_s, t0, t1) for t0, t1 in taken):
        return jsonify({"error": "That slot was just booked by someone else. Please pick another duration or time."}), 409

    db.execute(
        """INSERT INTO bookings (date, start_time, end_time, name, email, phone, notes, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)""",
        (day_str, start_s, final_end_s, name, email, phone, notes, datetime.utcnow().isoformat()),
    )
    db.commit()
    return jsonify({"ok": True, "duration": duration})

# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
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
    upcoming = db.execute(
        """SELECT * FROM bookings WHERE date >= ? AND status = 'confirmed'
           ORDER BY date ASC, start_time ASC""",
        (today_str,),
    ).fetchall()
    past = db.execute(
        """SELECT * FROM bookings WHERE date < ? AND status = 'confirmed'
           ORDER BY date DESC, start_time DESC LIMIT 50""",
        (today_str,),
    ).fetchall()
    cancelled = db.execute(
        """SELECT * FROM bookings WHERE status = 'cancelled'
           ORDER BY date DESC, start_time DESC LIMIT 50""",
    ).fetchall()
    blocked = db.execute(
        """SELECT * FROM blocked_slots WHERE date >= ? ORDER BY date ASC, start_time ASC""",
        (today_str,),
    ).fetchall()
    return render_template(
        "admin.html",
        studio_name=STUDIO_NAME,
        upcoming=upcoming,
        past=past,
        cancelled=cancelled,
        blocked=blocked,
        booking_link=request.host_url.rstrip("/") + url_for("book_page"),
    )

@app.route("/admin/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def admin_cancel_booking(booking_id):
    db = get_db()
    db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    db.commit()
    flash("Booking cancelled.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/booking/<int:booking_id>/delete", methods=["POST"])
@login_required
def admin_delete_booking(booking_id):
    db = get_db()
    db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    db.commit()
    flash("Booking deleted.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/block", methods=["POST"])
@login_required
def admin_block_slot():
    day_str = request.form.get("date", "").strip()
    start_s = request.form.get("start", "").strip()
    end_s = request.form.get("end", "").strip()
    reason = request.form.get("reason", "").strip()
    if day_str and start_s and end_s:
        db = get_db()
        db.execute(
            "INSERT INTO blocked_slots (date, start_time, end_time, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (day_str, start_s, end_s, reason, datetime.utcnow().isoformat()),
        )
        db.commit()
        flash("Time blocked off.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/block/<int:block_id>/delete", methods=["POST"])
@login_required
def admin_unblock_slot(block_id):
    db = get_db()
    db.execute("DELETE FROM blocked_slots WHERE id = ?", (block_id,))
    db.commit()
    flash("Block removed.")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  {STUDIO_NAME} booking app - FLEXIBLE DURATION")
    print(f"  Public booking page: http://localhost:{port}/")
    print(f"  Owner dashboard:     http://localhost:{port}/admin")
    print(f"  Admin password:      {'(set via DEVEN_ADMIN_PASSWORD env var)' if os.environ.get('DEVEN_ADMIN_PASSWORD') else ADMIN_PASSWORD}\n")
    app.run(debug=True, host="0.0.0.0", port=port)