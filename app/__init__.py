from dotenv import load_dotenv
import os
load_dotenv()

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_mail import Mail
import os

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()
mail = Mail()


def create_app():
    app = Flask(__name__, template_folder='../templates')

    # ---------- Core Flask config ----------
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')

    # Ensure SQLite DB is created programmatically inside instance/
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ---------- Redis & Caching ----------
    app.config['REDIS_URL'] = os.environ.get(
        'REDIS_URL',
        'redis://localhost:6379/0'
    )

    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_URL'] = app.config['REDIS_URL']
    app.config['CACHE_DEFAULT_TIMEOUT'] = 60

    # ---------- Celery (Redis broker & backend) ----------
    app.config['CELERY_BROKER_URL'] = app.config['REDIS_URL']
    app.config['CELERY_RESULT_BACKEND'] = app.config['REDIS_URL']

    # ---------- Mail configuration ----------
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False

    app.config['MAIL_USERNAME'] = os.environ.get(
        'MAIL_USERNAME',
        'your_email@example.com'
    )
    app.config['MAIL_PASSWORD'] = os.environ.get(
        'MAIL_PASSWORD',
        'your_password'
    )
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        app.config['MAIL_USERNAME']
    )

    # ---------- Init extensions ----------
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'login'

    # ---------- Register routes ----------
    from .routes import register_routes
    register_routes(app)

    # ---------- Create DB + default admin ----------
    with app.app_context():
        from .models import User
        from werkzeug.security import generate_password_hash

        db.create_all()

        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

    return app
