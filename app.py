import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True)
db_path = os.path.join(instance_path, 'the_deven.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    space = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

SPACES = {'daylight':'Daylight Studio','meeting':'Meeting Room','studio':'Studio'}
WORK_START=9
WORK_END=21

def get_all_slots(duration_hours):
    slots=[]
    for hour in range(WORK_START, WORK_END):
        for minute in (0,30):
            start_total=hour+minute/60
            end_total=start_total+duration_hours
            if end_total<=WORK_END:
                s_h=int(start_total); s_m=int((start_total-s_h)*60)
                e_h=int(end_total); e_m=int((end_total-e_h)*60)
                slots.append({'start':f"{s_h:02d}:{s_m:02d}",'end':f"{e_h:02d}:{e_m:02d}",'label':f"{s_h:02d}:{s_m:02d} - {e_h:02d}:{e_m:02d}"})
    return slots

@app.route('/')
def home(): return render_template('index.html')
@app.route('/book')
def book_page(): return render_template('book.html', spaces=SPACES)

@app.route('/api/slots')
def api_slots():
    try:
        date_str=request.args.get('date'); space=request.args.get('space','daylight'); duration=int(request.args.get('duration',1))
        if not date_str: return jsonify({'error':'date required'}),400
        try: datetime.strptime(date_str,'%Y-%m-%d')
        except: return jsonify({'error':'invalid date'}),400
        if space not in SPACES: space='daylight'
        booked=Booking.query.filter_by(date=date_str, space=space).all()
        booked_ranges=[(b.start_time,b.end_time) for b in booked]
        def is_overlap(s1,e1,s2,e2): return not (e1<=s2 or s1>=e2)
        all_slots=get_all_slots(duration)
        available=[]
        for slot in all_slots:
            overlap=False
            for b_start,b_end in booked_ranges:
                if is_overlap(slot['start'],slot['end'],b_start,b_end): overlap=True; break
            available.append({**slot,'available': not overlap})
        return jsonify({'date':date_str,'space':space,'duration':duration,'slots':available})
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'error':str(e),'slots':[]}),200

@app.route('/api/book', methods=['POST'])
def api_book():
    try:
        data=request.json
        for f in ['space','date','start_time','end_time','duration','name','phone']:
            if not data.get(f): return jsonify({'success':False,'message':f'{f} required'}),400
        existing=Booking.query.filter_by(date=data['date'], space=data['space']).all()
        for b in existing:
            if not (data['end_time']<=b.start_time or data['start_time']>=b.end_time):
                return jsonify({'success':False,'message':'Slot already booked'}),400
        new_booking=Booking(space=data['space'],date=data['date'],start_time=data['start_time'],end_time=data['end_time'],duration=int(data['duration']),customer_name=data['name'],customer_phone=data['phone'])
        db.session.add(new_booking); db.session.commit()
        return jsonify({'success':True})
    except Exception as e:
        return jsonify({'success':False,'message':str(e)}),500

@app.route('/admin')
def admin():
    bookings=Booking.query.order_by(Booking.date.desc()).all()
    return render_template('admin.html', bookings=bookings, spaces=SPACES)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
