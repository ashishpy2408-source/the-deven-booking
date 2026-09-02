# The Deven — Studio Booking

A small, self-hosted booking tool for a rentable studio, similar in spirit to
Cal.com but scoped to exactly what you asked for:

- **One link you share with creators/renters** — it shows *only* a calendar
  and open time slots. No other information about your business, other
  bookings, or admin tools is visible there.
- **Already-booked slots show as unavailable** (greyed out, can't be
  clicked) — but the page never reveals *who* booked them.
- **You (the owner)** log into a separate `/admin` dashboard with a
  password, where you see full details for every booking: name, email,
  phone, and any notes — plus the ability to cancel a booking or block off
  time for yourself (maintenance, personal shoots, etc.).

## 1. Install

Requires Python 3.9+.

```bash
cd the-deven-booking
pip install -r requirements.txt
```

## 2. Set your admin password (recommended)

By default the admin password is `changeme123` — change it before sharing
your link with anyone:

```bash
export DEVEN_ADMIN_PASSWORD="something-only-you-know"
```

(On Windows: `set DEVEN_ADMIN_PASSWORD=something-only-you-know`)

## 3. Run it

```bash
python app.py
```

- Public booking page: **http://localhost:5000/**  ← this is the link you share
- Owner dashboard: **http://localhost:5000/admin**

A local file `the_deven.db` (SQLite) is created automatically to store
bookings — no external database needed.

## 4. Customize for your studio

Open `app.py` and edit the block near the top:

```python
STUDIO_NAME = "The Deven"
STUDIO_TAGLINE = "A daylight studio for photo, film, and sound."
STUDIO_LOCATION = "Raipur, Chhattisgarh"
SESSION_LENGTH_MINUTES = 60      # length of one bookable slot
OPEN_HOUR = 9                    # studio opens
CLOSE_HOUR = 20                  # last slot must end by this hour
BOOKABLE_DAYS_AHEAD = 60         # how far ahead people can book
CLOSED_WEEKDAYS = set()          # e.g. {6} to close on Sundays (0=Mon..6=Sun)
```

## 5. Sharing the link with renters

Just send them `http://your-domain-or-ip:5000/` (or whatever URL it's
deployed at). That page has no navigation to `/admin` and no way to see
other people's booking details — it only shows dates/times and whether a
slot is open.

## 6. Putting this online (so the link works for anyone, not just your own computer)

Running `python app.py` only serves it on your machine. To get a real
shareable link, deploy it to a small host — Render, Railway, Fly.io, or a
basic VPS all work well with Flask apps like this one. In production, run
it behind a proper WSGI server instead of the Flask dev server, e.g.:

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

and make sure `DEVEN_ADMIN_PASSWORD` and `DEVEN_SECRET_KEY` are set as
environment variables on the host rather than left at their defaults.

## Notes on what's intentionally simple

- One fixed session length (set by `SESSION_LENGTH_MINUTES`) rather than
  multiple event types — this keeps the availability logic reliable. If you
  want different session lengths (e.g. 1-hour vs half-day), that's a
  reasonable next step to add.
- No email notifications yet — bookings show up in `/admin` immediately;
  wiring up confirmation emails (e.g. via SMTP or an email API) is a clean
  addition if you want it.
