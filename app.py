from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = "eleven-2025"
FILE = "bookings.json"
SPACES = ["Daylight Studio", "Meeting Room"]
START, END = 9, 21

def load():
    if os.path.exists(FILE):
        try:
            with open(FILE) as f: return json.load(f)
        except: return []
    return []

def save(data):
    with open(FILE, "w") as f: json.dump(data, f)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        space = request.form.get("space")
        duration = int(request.form.get("duration", 1))
        date = request.form.get("date")
        slot = request.form.get("slot")
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        bookings = load()
        ns = int(slot.split(":")[0]); ne = ns + duration
        for b in bookings:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0]); be = bs + int(b.get("duration", 1))
                if not (ne <= bs or ns >= be):
                    flash("Slot already booked!", "error")
                    return redirect(url_for("book"))
        bookings.append({"date": date, "space": space, "start": slot, "duration": duration, "name": name, "phone": phone, "email": email, "created": datetime.now().isoformat()})
        save(bookings)
        flash(f"Booked {space} {date} {slot}", "success")
        return redirect(url_for("book"))
    return render_template("book.html")

@app.route("/api/slots")
def slots():
    date = request.args.get("date")
    space = request.args.get("space", "Daylight Studio")
    duration = int(request.args.get("duration", 1))
    if not date: return jsonify({"slots": []})
    last = END - duration
    all_slots = []
    for h in range(START, last + 1):
        s = f"{h:02d}:00"; e = f"{h+duration:02d}:00"
        all_slots.append({"start": s, "end": e, "label": f"{s} - {e}", "time": s, "value": s})
    bookings = load()
    avail = []
    for sl in all_slots:
        ss = int(sl["start"].split(":")[0]); se = ss + duration
        conflict = False
        for b in bookings:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0]); be = bs + int(b.get("duration", 1))
                if not (se <= bs or ss >= be): conflict = True; break
        if not conflict: avail.append(sl)
    return jsonify({"slots": avail})

@app.route("/admin")
def admin():
    return render_template("admin.html", bookings=sorted(load(), key=lambda x: x["date"], reverse=True))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
