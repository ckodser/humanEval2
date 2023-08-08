from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# from cryptography.fernet import Fernet

import os

db = SQLAlchemy()
migrate = Migrate()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "ckodser1380"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    # app.config['SQLALCHEMY_POOL_SIZE'] = 10
    # app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10
    # app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    db.init_app(app)
    from .models import User

    create_database(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    with app.app_context():
        if not os.path.exists(os.path.join("./instance/", DB_NAME)):
            db.create_all()
            print('Created Database!')
