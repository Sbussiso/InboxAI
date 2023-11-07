from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path, environ
from flask_login import LoginManager
from flask_migrate import Migrate

#initialaze new server
db = SQLAlchemy()
DB_NAME = "database.db"

#creates application and intializes secret key
def create_app():
    application = Flask(__name__)
    application.config['SECRET_KEY'] = environ.get('SECRET_KEY', 'default_fallback_key')
    application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}' # locates database
    db.init_app(application) # initialize database

    # initialize Flask-Migrate after SQLAlchemy
    migrate = Migrate(application, db)

    from .views import views
    from .auth import auth

    application.register_blueprint(views, url_prefix='/')
    application.register_blueprint(auth, url_prefix='/')

    from .models import User

    with application.app_context():
        db.create_all()


    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(application)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))



    return application



def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')