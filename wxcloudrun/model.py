# wxcloudrun/model.py
from datetime import datetime
from wxcloudrun import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), unique=True, nullable=False)  # openid
    nick_name = db.Column(db.String(50))
    avatar_url = db.Column(db.String(255))
    currency = db.Column(db.String(10), default='CNY', nullable=False)
    status = db.Column(db.SmallInteger, default=1, nullable=False)
    phone = db.Column(db.String(20), nullable=True, unique=True, comment='手机号')
    email = db.Column(db.String(100), nullable=True, unique=True, comment='邮箱')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.Enum('income', 'expense'), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    icon = db.Column(db.String(50))
    color  = db.Column(db.String(20))
    is_hidden = db.Column(db.SmallInteger, default=0, nullable=False)
    sort = db.Column(db.Integer, default=0, nullable=False)
    is_preset = db.Column(db.SmallInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.Enum('income', 'expense'), nullable=False)
    amount_cent = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.BigInteger, db.ForeignKey('categories.id'), nullable=False)
    category_name_snapshot = db.Column(db.String(30))
    note = db.Column(db.String(200))
    occur_at = db.Column(db.DateTime, nullable=False)
    is_hidden = db.Column(db.SmallInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), db.ForeignKey('users.user_id'), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    amount_cent = db.Column(db.Integer, nullable=False)
    alert_enabled = db.Column(db.SmallInteger, default=1, nullable=False)
    alerted = db.Column(db.SmallInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
