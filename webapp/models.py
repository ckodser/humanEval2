import datetime

from flask_login import UserMixin
from sqlalchemy import func

from webapp import db

batch_size = 25
models = ["ORG_diff", "OBC_diff_4.1_4.2_fc"]


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True)
    password = db.Column(db.String(250))
    is_trained = db.Column(db.Integer)
    current_task = db.Column(db.Integer, default=-1)
    allowed_tasks = db.Column(db.Integer, default=batch_size)
    is_admin = db.Column(db.Integer, default=0)


class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pass_num = db.Column(db.String(200))
    sample = db.Column(db.String(200))
    helper = db.Column(db.String(200))
    option0 = db.Column(db.String(200))
    option1 = db.Column(db.String(200))
    choice = db.Column(db.String(200))
    starting_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ending_time = db.Column(db.DateTime)


class Encrypt(db.Model):
    raw = db.Column(db.String(200), primary_key=True)
    enc = db.Column(db.String(200))
