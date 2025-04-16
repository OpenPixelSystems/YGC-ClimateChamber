import os
from flask import Flask
import app.backend.services.state as state

app_state = state.AppState()

def create_app():
    app = Flask(__name__, static_url_path='/static')
    app.secret_key = os.urandom(24)
    app.config['JSON_AS_ASCII'] = False

    from app.routes.main import main_bp
    from app.routes.setup_graph import graph_bp
    from app.routes.climate_chamber_control import sensor_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(sensor_bp)

    return app