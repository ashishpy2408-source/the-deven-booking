from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "eleven-studio-2025-final"

BOOKINGS = []
SPACES = ["Daylight Studio", "Meeting Room"]
START, END = 9, 21
ADMIN_PASS = "Eleven@2025" # <-- Aapka admin password

@app.route("/", methods=["GET", "POST"])
@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        try:
            space = request.form.get("space", "Daylight Studio")
            duration = int(request.form.get("duration", 1))
            date = request.form.get("date")
            slot = request.form.get("slot")
            name = request.form.get("name")
            phone = request.form.get("phone")
            email = request.form.get("email")
            ns = int(slot.split(":")[0]); ne = ns + duration
            for b in BOOKINGS:
                if b["date"] == date and b["space"] == space:
                    bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                    if not (ne <= bs or ns >= be):
                        return f"<h2>Already Booked</h2><a href='/book'>Back</a>"
            BOOKINGS.append({"date": date, "space": space, "start": slot, "duration": duration, "name": name, "phone": phone, "email": email})
            return f"<h2 style='font-family:serif;text-align:center;margin-top:100px'>Booking Confirmed for {name}!<br><br>{space} - {date} - {slot}<br><br><a href='/book'>OK</a></h2>"
        except Exception as e:
            return f"Error {e} <a href='/book'>Back</a>"
    return render_template("book.html")

@app.route("/api/slots")
def api_slots():
    date = request.args.get("date", "")
    space = request.args.get("space", "Daylight Studio")
    try: duration = int(request.args.get("duration", 1))
    except: duration = 1
    if not date: return jsonify({"slots": []})
    last = END - duration
    slots = []
    for h in range(START, last + 1):
        s = f"{h:02d}:00"; e = f"{h+duration:02d}:00"
        slots.append({"start": s, "end": e, "label": f"{s} - {e}", "value": s})
    avail = []
    for sl in slots:
        ss = int(sl["start"].split(":")[0]); se = ss + duration; conf = False
        for b in BOOKINGS:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                if not (se <= bs or ss >= be): conf = True; break
        if not conf: avail.append(sl)
    return jsonify({"slots": avail})

# --- ADMIN WITH PASSWORD ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin_login.html", error="Wrong password")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return render_template("admin.html", bookings=BOOKINGS[::-1])

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
