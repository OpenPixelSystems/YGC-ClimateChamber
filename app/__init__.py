import os
from flask import Flask

"""App_state initialisation."""
from app.backend.app_state import get_app_state

def create_app():
    app = Flask(__name__,
            static_folder='frontend/static',
            static_url_path='/static',
            template_folder='frontend/templates')
    app.secret_key = os.urandom(24)
    app.config['JSON_AS_ASCII'] = False

    # Initialize AppState singleton
    app.state = get_app_state()

    from app.routes.home import home_bp
    from app.routes.graph_setup import graph_bp
    from app.routes.climate_control import climate_bp
    from app.routes.data_viewer import viewer_bp
    from app.routes.system_config import config_bp
    from app.routes.logs_viewer import logs_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(climate_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(logs_bp)

    return app