from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'Admin', 'Safety Officer'

class Violation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    violation_type = db.Column(db.String(50), nullable=False)  # 'No Helmet', 'No Vest'
    snapshot_path = db.Column(db.String(255), nullable=True)
    is_notified = db.Column(db.Boolean, default=False)

class DailyStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    total_detections = db.Column(db.Integer, default=0)
    total_violations = db.Column(db.Integer, default=0)
    helmet_compliance = db.Column(db.Float, default=100.0)
    vest_compliance = db.Column(db.Float, default=100.0)
