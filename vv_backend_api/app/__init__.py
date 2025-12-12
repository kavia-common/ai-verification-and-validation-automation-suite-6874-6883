from flask import Flask
from flask_cors import CORS
from flask_smorest import Api

from .routes.health import blp as health_blp
from .routes.api import blp as api_blp
from .db import init_db

app = Flask(__name__)
app.url_map.strict_slashes = False

# CORS: allow all origins for now; consider tightening for prod
CORS(app, resources={r"/*": {"origins": "*"}})

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
init_db(app)
