from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='شركة مصر العليا لتوزيع الكهرباء')
    sectors = db.relationship('Sector', backref='company', lazy=True)

class Sector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='قطاع أسيوط جنوب')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    engineerings = db.relationship('Engineering', backref='sector', lazy=True)

class Engineering(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sector.id'), nullable=False)

class Personnel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # مهندس، رئيس فرقة، فني، عامل، سائق
    engineering_id = db.Column(db.Integer, db.ForeignKey('engineering.id'), nullable=False)

class ComponentType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    unit = db.Column(db.String(20), default='عدد')  # عدد، كم

class MonthlyTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    engineering_id = db.Column(db.Integer, db.ForeignKey('engineering.id'), nullable=False)
    component_type_id = db.Column(db.Integer, db.ForeignKey('component_type.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)          # سنة البداية (مثل 2026)
    month = db.Column(db.Integer, nullable=False)         # 1-12 حيث 7=يوليو، 1=يناير، 6=يونيو
    target_value = db.Column(db.Float, nullable=False)
    __table_args__ = (db.UniqueConstraint('engineering_id', 'component_type_id', 'year', 'month', name='unique_monthly_target'),)

class MaintenanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    engineering_id = db.Column(db.Integer, db.ForeignKey('engineering.id'), nullable=False)
    component_type_id = db.Column(db.Integer, db.ForeignKey('component_type.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    executed_value = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    personnel_ids = db.Column(db.String(200))
    media_paths = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    engineering = db.relationship('Engineering', backref='logs')
    component_type = db.relationship('ComponentType', backref='logs')

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('maintenance_log.id'), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)