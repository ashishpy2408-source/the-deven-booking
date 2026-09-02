from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
import os
import requests

app = Flask(__name__)
app.secret_key = "the-deven-final-permanent-2026"

NPOINT_ID = "49e07bd08d8c357bc8a3"
NPOINT_URL = f"https://api.npoint.io/{NPOINT_ID}"

ADMIN_PASS = "TheDeven@2026!"
START, END = 9, 21

def load_bookings():
    try:
        r = requests.get(NPOINT_URL, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"Load error: {e}")
    return []

def save_bookings(data):
    try:
        requests.post(NPOINT_URL, json=data, timeout=15)
    except Exception as e:
        print(f"Save error: {e}")

@app.route("/")
@app.route("/book")
def book_page():
    return render_template("book.html")

@app.route("/book", methods=["POST"])
def book_submit():
    space = request.form.get("space", "Daylight Studio")
    duration = int(request.form.get("duration", 1))
    date = request.form.get("date")
    slot = request.form.get("slot")
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")

    bookings = load_bookings()
    ns = int(slot.split(":")[0])
    ne = ns + duration

    for b in bookings:
        if b["date"] == date and b["space"] == space:
            bs = int(b["start"].split(":")[0])
            be = bs + int(b["duration"])
            if not (ne <= bs or ns >= be):
                return "<h2 style='text-align:center;margin-top:100px'>Slot Already Booked!<br><br><a href='/book'>Go Back</a></h2>"

    bookings.append({
        "date": date, "space": space, "start": slot,
        "duration": duration, "name": name,
        "phone": phone, "email": email,
        "created": datetime.now().isoformat()
    })
    save_bookings(bookings)
    return f"<h2 style='text-align:center;margin-top:100px;font-family:serif'>Booking Confirmed!<br>{name} - {space}<br>{date} at {slot} for {duration}hr<br><br><a href='/book'>Done</a></h2>"

@app.route("/api/slots")
def api_slots():
    date = request.args.get("date", "")
    space = request.args.get("space", "Daylight Studio")
    try:
        duration = int(request.args.get("duration", 1))
    except:
        duration = 1
    if not date:
        return jsonify({"slots": []})

    bookings_live = load_bookings()
    last_start = END - duration
    all_slots = []
    for h in range(START, last_start + 1):
        if duration == 12 and h!= 9: continue
        if duration == 6 and h not in [9, 15]: continue
        s = f"{h:02d}:00"
        e = f"{h+duration:02d}:00"
        all_slots.append({"start": s, "end": e, "label": f"{s} - {e}", "value": s})

    avail = []
    for sl in all_slots:
        ss = int(sl["start"].split(":")[0])
        se = ss + duration
        conflict = False
        for b in bookings_live:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0])
                be = bs + int(b["duration"])
                if not (se <= bs or ss >= be):
                    conflict = True
                    break
        if not conflict:
            avail.append(sl)
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
