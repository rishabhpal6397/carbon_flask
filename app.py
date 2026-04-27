"""
CarbonIQ – Main Flask Application Entry Point

The cleanest fix for the mongo scoping problem:
  _mongo is a module-level PyMongo() instance.
  init_app() wires it to the Flask app at startup.
  get_mongo() simply returns _mongo — which by the time
  any request arrives, is fully initialised.
  Blueprints call get_mongo() *inside* view functions,
  never at import/module level.
"""

from flask import Flask, redirect, url_for

from flask_login import  current_user
from extensions import mongo, login_manager
from config import Config

# Module-level singletons — init_app() wires these to the app at startup.
# Blueprints must NEVER use these directly; call get_mongo() instead.


         # init_app() has already bound this by request time


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Bind extensions to this specific app instance
    mongo.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view    = "auth.login"
    login_manager.login_message = "Please log in to access your dashboard."

    # user_loader runs inside a request context — safe to call get_mongo()
    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.get_by_id( user_id)

    # Import blueprints here (inside factory) to avoid circular imports
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.api  import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("auth.login"))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()