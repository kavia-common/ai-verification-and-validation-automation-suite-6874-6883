from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
import os

from .routes.health import blp as health_blp
from .routes.api import blp as api_blp
from .db import init_db

app = Flask(__name__)
app.url_map.strict_slashes = False

# CORS configuration:
# Explicitly allow the local frontend at http://localhost:3000 for development.
# If REACT_APP_FRONTEND_URL env is set, use that; otherwise default to localhost:3000.
frontend_origin = os.getenv("REACT_APP_FRONTEND_URL", "http://localhost:3000").strip()
CORS(
    app,
    resources={r"/*": {"origins": [frontend_origin]}},
    supports_credentials=True,
)

# OpenAPI / API metadata
app.config["API_TITLE"] = "V&V Automation API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

# Initialize API and register blueprints
api = Api(app)
api.register_blueprint(health_blp)
api.register_blueprint(api_blp)

# Initialize database and create tables
# init_db uses DATABASE_URL if present, otherwise falls back to SQLite under DATA_DIR.
init_db(app)
