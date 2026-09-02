from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = "the-deven-final-2026"

BOOK_FILE = "bookings.json"
SPACES = ["Daylight Studio", "Meeting Room"]
START, END = 9, 21
ADMIN_PASS = "Deven@123" # <-- Yahi password hai

def load_bookings():
    if os.path.exists(BOOK_FILE):
        try:
            with open(BOOK_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_bookings(data):
    try:
        with open(BOOK_FILE, "w") as f:
            json.dump(data, f)
    except: pass

BOOKINGS = load_bookings()

@app.route("/", methods=["GET", "POST"])
@app.route("/book", methods=["GET", "POST"])
def book():
    global BOOKINGS
    if request.method == "POST":
        try:
            space = request.form.get("space", "Daylight Studio")
            duration = int(request.form.get("duration", 1))
            date = request.form.get("date")
            slot = request.form.get("slot")
            name = request.form.get("name")
            phone = request.form.get("phone")
            email = request.form.get("email")

            BOOKINGS = load_bookings()
            ns = int(slot.split(":")[0]); ne = ns + duration
            for b in BOOKINGS:
                if b["date"] == date and b["space"] == space:
                    bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                    if not (ne <= bs or ns >= be):
                        return f"<h2 style='text-align:center;margin-top:100px'>Slot Already Booked!<br><br><a href='/book'>Go Back</a></h2>"

            BOOKINGS.append({"date": date, "space": space, "start": slot, "duration": duration, "name": name, "phone": phone, "email": email, "created": datetime.now().isoformat()})
            save_bookings(BOOKINGS)
            return f"<h2 style='text-align:center;margin-top:100px;font-family:serif'>Booking Confirmed!<br>{name} - {space}<br>{date} at {slot} for {duration}hr<br><br><a href='/book'>Done</a></h2>"
        except Exception as e:
            return f"Error: {e} <a href='/book'>Back</a>"
    return render_template("book.html")

@app.route("/api/slots")
def api_slots():
    date = request.args.get("date", "")
    space = request.args.get("space", "Daylight Studio")
    try: duration = int(request.args.get("duration", 1))
    except: duration = 1
    if not date: return jsonify({"slots": []})

    BOOKINGS_LIVE = load_bookings()
    last_start = END - duration
    all_slots = []
    for h in range(START, last_start + 1):
        # Full day sirf 9 baje, Half day 9 aur 15 baje
        if duration == 12 and h!= 9: continue
        if duration == 6 and h not in [9, 15]: continue
        s = f"{h:02d}:00"; e_h = h + duration
        e = f"{e_h:02d}:00"
        all_slots.append({"start": s, "end": e, "label": f"{s} - {e}", "value": s})

    avail = []
    for sl in all_slots:
        ss = int(sl["start"].split(":")[0]); se = ss + duration; conflict = False
        for b in BOOKINGS_LIVE:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                if not (se <= bs or ss >= be): conflict = True; break
        if not conflict: avail.append(sl)
    return jsonify({"slots": avail})

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["is_admin"] = True
            return redirect("/admin")
        return render_template("admin_login.html", error="Galat Password!")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    data = load_bookings()
    return render_template("admin.html", bookings=data[::-1])

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
