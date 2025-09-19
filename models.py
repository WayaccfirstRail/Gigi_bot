from app import db
from sqlalchemy.sql import func
from sqlalchemy import Integer, BigInteger, String, Text, DateTime, Boolean


class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(BigInteger, primary_key=True)
    username = db.Column(String(64), nullable=True)
    first_name = db.Column(String(120), nullable=True)
    join_date = db.Column(DateTime, default=func.now())
    total_stars_spent = db.Column(Integer, default=0)
    interaction_count = db.Column(Integer, default=0)
    last_interaction = db.Column(DateTime, default=func.now())
    
    # Relationships
    purchases = db.relationship('UserPurchase', backref='user', lazy=True, cascade='all, delete-orphan')
    vip_subscription = db.relationship('VipSubscription', backref='user', uselist=False, cascade='all, delete-orphan')
    loyal_fan = db.relationship('LoyalFan', backref='user', uselist=False, cascade='all, delete-orphan')
    backups = db.relationship('UserBackup', backref='user', lazy=True, cascade='all, delete-orphan')


class LoyalFan(db.Model):
    __tablename__ = 'loyal_fans'
    
    user_id = db.Column(BigInteger, db.ForeignKey('users.user_id'), primary_key=True)
    reason = db.Column(Text, nullable=True)
    date_marked = db.Column(DateTime, default=func.now())


class Response(db.Model):
    __tablename__ = 'responses'
    
    key = db.Column(String(100), primary_key=True)
    text = db.Column(Text, nullable=False)


class ContentItem(db.Model):
    __tablename__ = 'content_items'
    
    name = db.Column(String(200), primary_key=True)
    price_stars = db.Column(Integer, nullable=False)
    file_path = db.Column(Text, nullable=True)
    description = db.Column(Text, nullable=True)
    created_date = db.Column(DateTime, default=func.now())
    content_type = db.Column(String(50), default='browse')
    
    # Relationships
    purchases = db.relationship('UserPurchase', backref='content_item', lazy=True, cascade='all, delete-orphan')


class UserPurchase(db.Model):
    __tablename__ = 'user_purchases'
    
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    content_name = db.Column(String(200), db.ForeignKey('content_items.name'), nullable=False)
    purchase_date = db.Column(DateTime, default=func.now())
    price_paid = db.Column(Integer, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'content_name'),)


class ScheduledPost(db.Model):
    __tablename__ = 'scheduled_posts'
    
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(DateTime, nullable=False)
    content = db.Column(Text, nullable=False)
    created_date = db.Column(DateTime, default=func.now())


class UserBackup(db.Model):
    __tablename__ = 'user_backups'
    
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    username = db.Column(String(64), nullable=True)
    first_name = db.Column(String(120), nullable=True)
    join_date = db.Column(DateTime, nullable=True)
    total_stars_spent = db.Column(Integer, default=0)
    interaction_count = db.Column(Integer, default=0)
    last_interaction = db.Column(DateTime, nullable=True)
    backup_date = db.Column(DateTime, default=func.now())


class VipSubscription(db.Model):
    __tablename__ = 'vip_subscriptions'
    
    user_id = db.Column(BigInteger, db.ForeignKey('users.user_id'), primary_key=True)
    start_date = db.Column(DateTime, default=func.now())
    expiry_date = db.Column(DateTime, nullable=False)
    is_active = db.Column(Boolean, default=True)
    total_payments = db.Column(Integer, default=0)


class VipSetting(db.Model):
    __tablename__ = 'vip_settings'
    
    key = db.Column(String(100), primary_key=True)
    value = db.Column(Text, nullable=False)


class Teaser(db.Model):
    __tablename__ = 'teasers'
    
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    file_path = db.Column(Text, nullable=True)
    file_type = db.Column(String(50), nullable=True)
    description = db.Column(Text, nullable=True)
    created_date = db.Column(DateTime, default=func.now())
    vip_only = db.Column(Boolean, default=False)


class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'
    
    user_id = db.Column(BigInteger, primary_key=True, autoincrement=False)
    blocked_date = db.Column(DateTime, default=func.now())
    reason = db.Column(Text, nullable=True)
    blocked_by = db.Column(BigInteger, nullable=False)