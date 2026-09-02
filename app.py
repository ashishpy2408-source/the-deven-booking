from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "eleven-studio-2025"

SPACES = ["Daylight Studio", "Meeting Room"]
BOOKINGS = [] # Render par file error se bachne ke liye memory me rakha hai
START, END = 9, 21

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

            # overlap check
            ns = int(slot.split(":")[0]); ne = ns + duration
            for b in BOOKINGS:
                if b["date"] == date and b["space"] == space:
                    bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                    if not (ne <= bs or ns >= be):
                        return f"<h2>Slot Already Booked!</h2><p>{space} {date} {slot} already taken</p><a href='/book'>Go Back</a>"

            BOOKINGS.append({"date": date, "space": space, "start": slot, "duration": duration, "name": name, "phone": phone, "email": email, "created": datetime.now().isoformat()})
            return f"<h2>Booking Confirmed!</h2><p>Thank you {name}, {space} booked on {date} at {slot} for {duration}hr</p><a href='/book'>Book Another</a>"
        except Exception as e:
            return f"<h2>Error: {e}</h2><a href='/book'>Go Back</a>"

    return render_template("book.html")

@app.route("/api/slots")
def api_slots():
    date = request.args.get("date", "")
    space = request.args.get("space", "Daylight Studio")
    duration = int(request.args.get("duration", 1))
    if not date: return jsonify({"slots": []})
    last = END - duration
    all_slots = []
    for h in range(START, last + 1):
        s = f"{h:02d}:00"; e = f"{h+duration:02d}:00"
        all_slots.append({"start": s, "end": e, "label": f"{s} - {e}", "time": s, "value": s})
    avail = []
    for sl in all_slots:
        ss = int(sl["start"].split(":")[0]); se = ss + duration; conf = False
        for b in BOOKINGS:
            if b["date"] == date and b["space"] == space:
                bs = int(b["start"].split(":")[0]); be = bs + int(b["duration"])
                if not (se <= bs or ss >= be): conf = True; break
        if not conf: avail.append(sl)
    return jsonify({"slots": avail})

@app.route("/admin")
def admin():
    return render_template("admin.html", bookings=BOOKINGS[::-1])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
