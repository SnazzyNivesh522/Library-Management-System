from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from app.config import Config
from flask_apscheduler import APScheduler
from flask_migrate import Migrate


db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail = Mail()
scheduler = APScheduler()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    from app.main.routes import main
    from app.auth.routes import auth
    from app.books.routes import books
    from app.users.routes import users
    from app.admin.routes import admin
    from app.errors.handlers import errors 

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(books)
    app.register_blueprint(users)
    app.register_blueprint(admin)
    app.register_blueprint(errors)


    with app.app_context():
        db.create_all()
        print('Database tables created or verified.')


    return app