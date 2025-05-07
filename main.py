import os
import argparse
from flask import Flask, jsonify, request, send_file
from flasgger import Swagger

from src.utils import get_logger, load_config
from src.database import PostgreSQLManager
from src import ep_poi

# ENVIRONMENT VARIABLES
# --------------------------------------
from dotenv import load_dotenv
load_dotenv()

# LOGGER
# --------------------------------------
logger = get_logger(__name__)

# CONFIGURATION
# --------------------------------------
CONFIGURATION_FILE = "config/config.yaml"
CONFIG = load_config(CONFIGURATION_FILE)
IMAGES_DIR = CONFIG["images_dir"]

# ARGUMENTS
# --------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description="PostgreSQL Database Manager")
    parser.add_argument("-m", "--mode", type=str, default="develop", choices=["develop", "production"],
                        help="Deployment mode: develop or production")
    
    arguments = parser.parse_args()
    if arguments.mode not in ["develop", "production"]:
        logger.error("Invalid argument. Use 'develop' or 'production'.")
        exit(1)
    deployment = arguments.mode
    return deployment

# DATABASE CONNECTION
# --------------------------------------
db_manager = PostgreSQLManager(config=CONFIG["database"])

# FLASK APP
# --------------------------------------
app = Flask(__name__)

# SWAGGER
# --------------------------------------
SWAGGER_FILE = "config/swagger.yml"
swagger = Swagger(app, template_file=SWAGGER_FILE)

# ===========================================
# API ENDPOINTS
# ===========================================
@app.route("/", methods=["GET"])
def function_status():
    return jsonify({"status": "ok", "message": "Rurallure API is running"}), 200

@app.route("/pois/around", methods=["POST"])
def function_get_locations_around():
    body = request.get_json()
    if not body:
        return jsonify({"status": "error", "message": "Request body is empty"}), 400
    
    result = ep_poi.ep_pois_around(body, db_manager)

    if result["status"] != "ok":
        return jsonify(result), 400
    
    return jsonify(result), 200

@app.route("/pois/near-any", methods=["POST"])
def function_get_locations_near_any():
    body = request.get_json()
    if not body:
        return jsonify({"status": "error", "message": "Request body is empty"}), 400
    
    result = ep_poi.ep_pois_near_any(body, db_manager)
    if result["status"] != "ok":
        return jsonify(result), 400
    
    return jsonify(result), 200

@app.route("/poi/description", methods=["POST"])
def function_get_poi_description():
    body = request.get_json()
    if not body:
        return jsonify({"status": "error", "message": "Request body is empty"}), 400
    
    result = ep_poi.ep_poi_description(body, db_manager)
    if result["status"] != "ok":
        return jsonify(result), 400
    return jsonify(result), 200

@app.route("/image/<string:image_filename>", methods=["GET"])
def function_get_image(image_filename):
    # Get the image file path
    safe_filename = os.path.basename(image_filename)
    image_path = os.path.join(IMAGES_DIR, safe_filename)
    
    # Check if the file exists
    if not os.path.isfile(image_path):
        return jsonify({"status": "error", "message": "Image not found"}), 404
    
    # Return the image file
    return send_file(image_path, mimetype="image/gif"), 200

# =========================================
# MAIN FUNCTION
# =========================================
if __name__ == "__main__":    
    deployment_mode = parse_arguments()
    logger.info(f"Starting application in {deployment_mode} mode")

    host = CONFIG["api"]["host"]
    if deployment_mode == "production":
        port = CONFIG["api"]["production_port"]
    elif deployment_mode == "develop":
        port = CONFIG["api"]["develop_port"]
    else:
        logger.error(f"Unknown deployment mode '{deployment_mode}'")
        exit(1)
    
    logger.info(f"Starting Flask app on {host}:{port}")
    app.run(debug=False, host=host, port=port)




    


