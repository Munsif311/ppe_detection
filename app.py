from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from models import db, User, Violation, DailyStats
import os
import time
import numpy as np
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from camera import VideoCamera
import cv2
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ppe_monitoring_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Custom Jinja2 Filter
@app.template_filter('zfill')
def zfill_filter(s, width):
    return str(s).zfill(width)

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- ROUTES ---

@app.route('/')
def dashboard():
    total_violations = Violation.query.count()
    recent_violations = Violation.query.order_by(Violation.timestamp.desc()).limit(10).all()
    
    # Class-wise stats
    no_helmet_count = Violation.query.filter(Violation.violation_type.like('%helmet%')).count()
    no_vest_count = Violation.query.filter(Violation.violation_type.like('%vest%')).count()
    
    # Calculate percentages for progress bars
    no_helmet_pct = (no_helmet_count / total_violations * 100) if total_violations > 0 else 0
    no_vest_pct = (no_vest_count / total_violations * 100) if total_violations > 0 else 0
    
    stats = {
        'total_detections': 1850, # Simulated total detections
        'violations': total_violations,
        'compliance': 98.4,
        'no_helmet': no_helmet_count,
        'no_vest': no_vest_count,
        'no_helmet_pct': no_helmet_pct,
        'no_vest_pct': no_vest_pct,
        'uptime': '99.9%'
    }
    return render_template('dashboard.html', stats=stats, recent_violations=recent_violations)

@app.route('/cameras')
def cameras():
    return render_template('cameras.html')

@app.route('/analytics')
def analytics():
    total_violations = Violation.query.count()
    no_helmet_count = Violation.query.filter(Violation.violation_type.like('%helmet%')).count()
    no_vest_count = Violation.query.filter(Violation.violation_type.like('%vest%')).count()
    
    stats = {
        'total_detections': 1850,
        'violations': total_violations,
        'no_helmet': no_helmet_count,
        'no_vest': no_vest_count
    }
    return render_template('analytics.html', stats=stats)

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            time.sleep(0.1)

def dummy_gen(camera_id):
    # Generates a professional "Signal Processing" placeholder stream
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Background Navy
    frame[:] = (42, 23, 15) # BGR for Slate 900 #0f172a
    
    cv2.putText(frame, f"CAMERA {camera_id}: SIGNAL PROCESSING...", (380, 360), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (248, 189, 56), 2) # Sky blue text
    
    cv2.rectangle(frame, (100, 100), (1180, 620), (255, 255, 255), 1)
    
    ret, jpeg = cv2.imencode('.jpg', frame)
    dummy_frame = jpeg.tobytes()
    
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + dummy_frame + b'\r\n\r\n')
        time.sleep(1)

@app.route('/video_feed')
def video_feed():
    # Only initialize camera if needed to avoid blocking
    if not hasattr(app, 'camera_instance'):
        app.camera_instance = VideoCamera()
    return Response(gen(app.camera_instance),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/dummy_feed/<int:cam_id>')
def dummy_feed(cam_id):
    return Response(dummy_gen(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reports')
def reports():
    violations = Violation.query.order_by(Violation.timestamp.desc()).all()
    return render_template('alerts.html', violations=violations)

@app.route('/get_stats')
def get_stats():
    # Return JSON for dynamic dashboard updates
    total_violations = Violation.query.count()
    return jsonify({
        'total_detections': 1250, # Dummy for now
        'total_violations': total_violations,
        'compliance': 97.2
    })

@app.route('/get_alerts')
def get_alerts():
    # Poll for recent violations to show toasts
    latest = Violation.query.filter_by(is_notified=False).order_by(Violation.timestamp.desc()).all()
    alerts = []
    for a in latest:
        alerts.append({
            'id': a.id,
            'type': a.violation_type,
            'time': a.timestamp.strftime("%H:%M:%S")
        })
        a.is_notified = True
    db.session.commit()
    return jsonify(alerts)

# --- INITIALIZATION ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
            
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
