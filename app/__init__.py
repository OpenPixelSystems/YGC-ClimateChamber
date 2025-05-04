import os
from flask import Flask

"""App_state initialisation."""
from app.backend.services.app_state import get_app_state

def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.secret_key = os.urandom(24)
    app.config['JSON_AS_ASCII'] = False

    # Initialize AppState singleton
    app.state = get_app_state()

    from app.routes.main import main_bp
    from app.routes.setup_graph import graph_bp
    from app.routes.climate_chamber_control import sensor_bp
    from app.routes.database_viewer import viewer_bp
    from app.routes.configuration import config_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(sensor_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(config_bp)

    return app