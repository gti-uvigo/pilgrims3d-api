import requests
import db.dto as dto
from flask import Flask, jsonify, request
from flask_cors import CORS
from utils import get_route
import flasgger
import time 
import firebase_admin
from firebase_admin import credentials, messaging
from math import radians, cos, sin, sqrt, atan2
import utils

from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
import os
from dotenv import load_dotenv

load_dotenv(".env")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET")
jwt = JWTManager(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)

cred = credentials.Certificate("credentials_firebase.json")
firebase_admin.initialize_app(cred)

swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Rurallure API",
        "description": "Documentación de la API de rutas y puntos de interés de Rurallure.",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": " Enter yourJWT token as **Bearer <token>**"
        }
    }
}

@app.route('/routes', methods=['POST'])
def function_get_all_routes():
    """
    Endpoint to get all available routes in the API.
    ---
    tags:
      - Routes
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            route_type:
              type: string
              example: "cultural"
            type:
              type: string
              example: "main"
      - in: query
        name: language_id
        type: string
        required: false
        description: ID del idioma (opcional)
    responses:
      200:
        description: Lista de rutas encontradas
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Ruta no encontrada
    """
    body = request.get_json()
    
    route_type = body["route_type"]
    tipe = body["type"]
    language_id = body['language_id'] if 'language_id' in body else '6d68e409-c46e-4d4a-8560-f15256e9cbb3'

    print(f"Received route_type: {route_type}, type: {tipe}, language_id: {language_id}")

    result = dto.get_routes_descriptions_by_type(route_type=route_type, type=tipe, language_id=language_id)
    if not result:
        return jsonify({"status": "error", "message": "Route not found"}), 404

    return jsonify({"status": "ok", "data": result}), 200



@app.route('/route_stages', methods=['POST'])
def function_get_route_stages():
    """
    Endpoint to get all stages of a specific route.
    ---
    tags:
      - Routes
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            route_id:
              type: string
              example: "route123"
            language_id:
              type: string
              example: "6d68e409-c46e-4d4a-8560-f15256e9cbb3"
            user_id:
              type: string
              example: "user123"
    responses:
      200:
        description: Lista de etapas de la ruta
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Ruta no encontrada
    """
    body = request.get_json()
    route_id = body.get('route_id', None)
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    user_id = body.get('user_id', None)

    result = dto.get_route_stages(route_id)
    print(result)
    if not result:
        return jsonify({"status": "error", "message": "Route not found"}), 404

    for stage in result:
        for idx, poi in enumerate(stage.get("points_of_interest", [])):
            poi_data = dto.get_poi_by_id(poi["id"], language_id=language_id)
            if poi_data:
                stage["points_of_interest"][idx]["title"] = poi_data.get("title")
                stage["points_of_interest"][idx]["image_id"] = poi_data.get("image_id")
                stage["points_of_interest"][idx]["types"] = poi_data.get("types")
                stage["points_of_interest"][idx]["latitude"] = poi_data.get("latitude")
                stage["points_of_interest"][idx]["longitude"] = poi_data.get("longitude")
                stage["points_of_interest"][idx]["is_mobility_friendly"] = poi_data.get("is_mobility_friendly")
                stage["points_of_interest"][idx]["rating"] = poi_data.get("rating")
                stage["points_of_interest"][idx]["user_rating"] = dto.get_user_rating_for_poi(user_id, poi["id"]) if user_id else None
    return jsonify({"status": "ok", "data": result}), 200


@app.route("/rate_poi", methods=["POST"])
def function_rate_poi():
  """
  Endpoint to rate a point of interest (POI).
  ---
  tags:
    - POI
  parameters:
    - in: body
      name: body
      required: true
      schema:
        type: object
        properties:
          poi_id:
            type: string
            example: "poi123"
          user_id:
            type: string
            example: "user123" 
          rating:
            type: integer
            example: 4
  responses:
    200:
      description: Calificación registrada exitosamente
      schema:
        type: object
        properties:
          status:
            type: string
          data:
            type: object
    400:
      description: Datos de entrada inválidos
  """
  body = request.get_json()
  poi_id = body.get('poi_id', None)
  user_id = body.get('user_id', None)
  rating = body.get('rating', None)

  if not poi_id or not user_id or rating is None:
      return jsonify({"status": "error", "message": "Missing required fields"}), 400

  new_rating = dto.rate_poi(user_id=user_id, poi_id=poi_id, score=rating)
  print("----------------------------------New rating:", new_rating)

  return jsonify({"status": "ok", "data": new_rating}), 200

@app.route('/route_locations/<route_id>', methods=['GET'])
def function_get_route_locations(route_id):
    """
    Endpoint to get all locations of a specific route.
    ---
    tags:
      - Routes
    parameters:
      - in: path
        name: route_id
        type: string
        required: true
        description: ID de la ruta
    responses:
      200:
        description: Lista de localizaciones de la ruta
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Localizaciones de la ruta no encontradas
    """
    all_route = dto.get_route_locations(route_id)
    
    if not all_route:
        return jsonify({"status": "error", "message": "Route locations not found"}), 404
    
    
    return jsonify({"status": "ok", "data": all_route}), 200

@app.route('/route_locations/<route_id>', methods=['POST'])
def function_get_route_locations_start(route_id):
    """
    Endpoint to get all locations of a specific route from a start point.
    ---
    tags:
      - Routes
    parameters:
      - in: path
        name: route_id
        type: string
        required: true
        description: ID de la ruta
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            start_points:
              type: array
              items:
                type: number
              example: [42.123, -3.456]
    responses:
      200:
        description: Localizaciones de la ruta y ruta hasta el inicio
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      400:
        description: Cuerpo de la petición inválido
      404:
        description: Localizaciones de la ruta no encontradas
    """
    body = request.get_json()
    if not body or "start_points" not in body or "end_points" not in body:
        return jsonify({"status": "error", "message": "Invalid request body"}), 400
    
    route_start = body.get("start_points")
    all_route = dto.get_route_locations(route_id)

    route_end = body.get("end_points")


    if not all_route:
        return jsonify({"status": "error", "message": "Route locations not found"}), 404

    route_to_locations = get_route(route_start, route_end, profile="foot")

    if not route_to_locations:
        # return jsonify({"status": "error", "message": "Route not found"}), 404
        route_to_locations = []
    result = {
        "all_route": all_route[0]["locations"]["all_points"],
        "route_to_start": route_to_locations
    }
    
    return jsonify({"status": "ok", "data": result}), 200


@app.route('/poi/<poi_id>', methods=['GET'])
def function_get_poi_by_id(poi_id):
    """
    Endpoint to get a point of interest (POI) by its ID.
    ---
    tags:
      - POI
    parameters:
      - in: path
        name: poi_id
        type: string
        required: true
        description: ID del punto de interés
      - in: query
        name: language_id
        type: string
        required: false
        description: ID del idioma (opcional)
    responses:
      200:
        description: Punto de interés encontrado
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      404:
        description: Punto de interés no encontrado
    """
    language_id = request.args.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    result = dto.get_poi_by_id(poi_id, language_id)
    
    if not result:
        return jsonify({"status": "error", "message": "POI not found"}), 404
    
    return jsonify({"status": "ok", "data": result}), 200



@app.route('/languages', methods=['GET'])
def function_get_languages():
    """
    Endpoint to get all available languages.
    ---
    tags:
      - Languages
    responses:
      200:
        description: Lista de idiomas disponibles
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Idiomas no encontrados
    """
    result = dto.get_languages()
    
    if not result:
        return jsonify({"status": "error", "message": "Languages not found"}), 404
    
    return jsonify({"status": "ok", "data": result}), 200



@app.route('/route_types', methods=['GET'])
def function_get_route_types():
    """
    Endpoint to get all available route types.
    ---
    tags:
      - Routes
    responses:
      200:
        description: Lista de tipos de ruta disponibles
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Tipos de ruta no encontrados
    """
    result = dto.get_route_types()
    
    if not result:
        return jsonify({"status": "error", "message": "Route types not found"}), 404
    
    return jsonify({"status": "ok", "data": result}), 200


@app.route('/create_route_type', methods=['POST'])
def function_create_route_type():
    """
    """
    body = request.get_json()
    name = body.get('name', None)
    

    route_type = dto.create_route_type(name)

    return jsonify({"status": "ok", "data": route_type}), 200



@app.route('/images/<image_id>', methods=['GET'])
def function_download_image(image_id):
    """
    Endpoint to download an image stored in GridFS by its ID.
    ---
    tags:
      - Images
    parameters:
      - in: path
        name: image_id
        type: string
        required: true
        description: ID de la imagen
    responses:
      200:
        description: Imagen encontrada
      404:
        description: Imagen no encontrada
    """
    response = dto.get_image_by_id(image_id)
    
    if response is None:
        return jsonify({"status": "error", "message": "Image not found"}), 404
    
    return response

@app.route('/image/<image_id>', methods=['GET'])
@jwt_required()
def function_download_image_tm(image_id):
    """
    Endpoint to download an image stored in GridFS by its ID.
    ---
    tags:
      - Images
    parameters:
      - in: path
        name: image_id
        type: string
        required: true
        description: ID de la imagen
    responses:
      200:
        description: Imagen encontrada
      404:
        description: Imagen no encontrada
    """
    claims = get_jwt()
    rate_limit = claims.get("rate_limit", "10 per minute")  # valor por defecto
    @limiter.limit(rate_limit)
    def download_image():
        response = dto.get_image_by_id(image_id)
        
        if response is None:
            return jsonify({"status": "error", "message": "Image not found"}), 404

        return response
    return download_image()

@app.route("/pois_types/<language_id>", methods=["GET"])
def function_get_pois_types(language_id):  
    """
    Endpoint to get all available POI types.
    ---
    tags:
      - POI Types
    parameters:
      - in: path
        name: language_id
        type: string
        required: true
        description: ID del idioma
    responses:
      200:
        description: Lista de tipos de POIs disponibles
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Tipos de POIs no encontrados
    """
    result = dto.get_pois_types(language_id)
    
    if not result:
        return jsonify({"status": "error", "message": "POI types not found"}), 404
    
    return jsonify({"status": "ok", "data": result}), 200


@app.route('/pois_by_route/<route_id>', methods=['GET'])
def function_get_pois_by_route(route_id):
    """
    Endpoint to get all points of interest (POIs) for a specific route.
    ---
    tags:
      - POI
    parameters:
      - in: path
        name: route_id        
        type: string
        required: true
        description: ID de la ruta
      - in: query
        name: language_id
        type: string
        required: false
        description: ID del idioma (opcional)
    responses:
      200:
        description: Lista de puntos de interés encontrados
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Ruta o puntos de interés no encontrados
    """
    language_id = request.args.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    result = dto.get_route_stages(route_id)

    pois = []

    for stage in result:
        for idx, poi in enumerate(stage.get("points_of_interest", [])):
            poi_data = dto.get_poi_by_id(poi["id"], language_id=language_id)
            if poi_data:
                pois.append(poi_data)


    
    if not result:
        return jsonify({"status": "error", "message": "Route or POIs not found"}), 404
    
    return jsonify({"status": "ok", "data": pois}), 200


# ===== RUTA PARA CREAR TOKENS PERSONALIZADOS =====
@app.route("/generate-token", methods=["POST"])
def generate_token():
    """
    Endpoint to generate a custom JWT token with specific claims.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            expires_minutes:
              type: integer
              example: 15
            rate_limit:
              type: string
              example: "10 per minute"
            admin_key:
              type: string
              example: "your_admin_key"
    responses: 
      200:
        description: Token generated successfully
        schema:
          type: object
          properties:
            access_token:
              type: string
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      403:
        description: Invalid admin key
      400:
        description: Invalid request body
    """
    data = request.get_json()
    expires_minutes = data.get("expires_minutes", 15)
    rate_limit = data.get("rate_limit", "10 per minute")
    admin_key = data.get("admin_key", None)

    if admin_key != os.getenv("ADMIN_KEY"):
        return jsonify({"status": "error", "message": "Invalid admin key"}), 403

    # Genera un token con claims personalizados
    additional_claims = {
        "rate_limit": rate_limit
    }

    access_token = create_access_token(
        identity="custom_user",
        additional_claims=additional_claims,
        expires_delta=datetime.timedelta(minutes=expires_minutes)
    )

    return jsonify(access_token=access_token)


@app.route('/get_all_pois', methods=['GET'])
@jwt_required()
def function_get_all_pois():
    """
    Endpoint to get all points of interest (POIs).
    ---
    tags:
      - POI
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: language_id
        type: string
        required: false
        description: Optional language ID
    responses:
      200:
        description: List of found points of interest
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
      404:
        description: Points of interest not found
    """
    claims = get_jwt()
    rate_limit = claims.get("rate_limit", "5 per minute")  # valor por defecto

    @limiter.limit(rate_limit)
    def inner():
        result = dto.get_all_pois()
        
        if not result:
            return jsonify({"status": "error", "message": "POIs not found"}), 404
        
        return jsonify({"status": "ok", "data": result}), 200

    return inner()



@app.route('/get_pois_in_a_region', methods=['POST'])
def get_pois_in_a_region():
    """
    """
    body = request.get_json()
    north = body.get('north', None)
    south = body.get('south', None)
    east = body.get('east', None)
    west = body.get('west', None)
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    pois = dto.get_pois_in_a_region(north, south, east, west, language_id=language_id)
    return jsonify({"status": "ok", "data": pois}), 200



@app.route('/get_pois_with_zenodo_url', methods=['POST'])
def get_pois_with_zenodo_url():
    """
    Endpoint to get all POIs that have a Zenodo URL.
    ---
    tags:
      - POI
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            language_id:
              type: string
              example: "6d68e409-c46e-4d4a-8560-f15256e9cbb3"
    responses:
      200:
        description: POIs retrieved successfully
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  zenodo_url:
                    type: string
      404:
        description: No POIs found with Zenodo URL
    """
    body = request.get_json() 
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    pois = dto.get_pois_with_zenodo_url(language_id=language_id)
    if not pois:
        return jsonify({"status": "error", "message": "No POIs found with Zenodo URL"}), 404

    return jsonify({"status": "ok", "data": pois}), 200


@app.route('/get_poi/<poi_id>', methods=['GET'])
@jwt_required()
def function_get_poi_by_id_ext(poi_id):
    """
    Endpoint to get a point of interest (POI) by its ID.
    ---
    tags:
      - POI
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: poi_id
        type: string
        required: true
        description: POI ID
      - in: query
        name: language_id
        type: string
        required: false
        description: Optional language ID
    responses:
      200:
        description: POI found
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      404:
        description: POI not found
    """
    claims = get_jwt()
    rate_limit = claims.get("rate_limit", "10 per minute")  # valor por defecto

    @limiter.limit(rate_limit)
    def inner():
        language_id = request.args.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
        result = dto.get_poi_by_id(poi_id, language_id)
        
        if not result:
            return jsonify({"status": "error", "message": "POI not found"}), 404
        
        return jsonify({"status": "ok", "data": result}), 200

    return inner()




@app.route('/update_poi', methods=['POST'])
def update_poi():
    """
    """
    body = request.get_json() 
    poi = body.get('poi', None)

    if not poi:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    poi = dto.update_poi(poi)

    return jsonify({"status": "ok", "data": "Poi updated successfully"}), 200



@app.route('/get_all_routes_by_route_type', methods=['POST'])
def get_all_routes_by_route_type():
    """
    """
    body = request.get_json() 
    route_type_id = body.get('route_type', None)
    lang_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    result = dto.get_all_routes_by_route_type(route_type_id, lang_id)

    return jsonify({"status": "ok", "data": result}), 200


@app.route('/register_user', methods=['POST'])
def register_user():
    """
    Endpoint to register a new user.
    ---
    tags:
      - Users
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            fcm_token:
              type: string
              example: "132231234"
            id_token:
              type: string
              example: "433352562"
            email:
              type: string
              example: "user@example.com"
            latitude:
              type: number
              example: 42.123456
            longitude:
              type: number
              example: -71.123456
            timestamp:
              type: string
              example: "2023-10-01T12:00:00Z"
    responses:
      200:
        description: Usuario registrado exitosamente
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      400:
        description: Datos de entrada inválidos
    """
    body = request.get_json()
    fcm_token = body.get('fcm_token', None)
    id_token = body.get('id_token', None)
    email = body.get('email', None)
    latitude = body.get('latitude', 0.0)
    longitude = body.get('longitude', 0.0)
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    if not id_token or not email:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    print("Registering user:", id_token, fcm_token, email, latitude, longitude, timestamp)

    test_user = dto.get_user_by_id(id_token)
    if test_user:
        dto.update_user(fcm_token, id_token, latitude, longitude, email, timestamp)
        return jsonify({"status": "ok", "data": test_user}), 200
    
    user = dto.register_user(fcm_token, id_token, email, latitude, longitude,  timestamp)

    return jsonify({"status": "ok", "data": user}), 200


@app.route('/update_user', methods=['POST'])
def update_user():
    """
    Endpoint to update an existing user.
    ---
    tags:
      - Users
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id_token:
              type: string
              example: "433352562"
            latitude:
              type: number
              example: 42.123456
            longitude:
              type: number
              example: -71.123456
            timestamp:
              type: string
              example: "2023-10-01T12:00:00Z"
    responses:
      200:
        description: Usuario actualizado exitosamente
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      400:
        description: Datos de entrada inválidos
    """
    body = request.get_json()
    id_token = body.get('id_token', None)
    latitude = body.get('latitude', 0.0)
    longitude = body.get('longitude', 0.0)
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    if not id_token:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    

    print("Updating user:", id_token, latitude, longitude, timestamp)

    user = dto.update_user(None, id_token, latitude, longitude, None, timestamp)

    return jsonify({"status": "ok", "data": user}), 200


@app.route('/send_notification_sos', methods=['POST'])
def send_notification_sos():
    """
    Endpoint to send a notification to a user.
    ---
    tags:
      - Notifications
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id_token:
              type: string
              example: "433352562"
    responses:
      200:
        description: Notificación enviada exitosamente
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: object
      400:
        description: Datos de entrada inválidos
    """
    body = request.get_json()
    id_token = body.get('id_token', None)
    if not id_token:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    user = dto.get_user_by_id(id_token)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    if not user.get("fcm_token", None):
        return jsonify({"status": "error", "message": "User has no FCM token"}), 404
    titulo = "SOS Alert"
    cuerpo = "{}, {}".format(user["latitude"], user["longitude"])
    

    ##Obtengo todo los usuarios de la base de datos, y veo aquellos que se actualizaran hace menos de 30 minutos y estan a menos de 1km
    all_users = dto.get_all_users()
    fcm_tokens_send = []
    for u in all_users:
        if u["id_token"] != id_token:
            tiempo_actual = time.gmtime()
            tiempo_usuario = time.strptime(u["last_active"], '%Y-%m-%dT%H:%M:%SZ')
            print(tiempo_actual)
            print(tiempo_usuario)
            diferencia_minutos = (time.mktime(tiempo_actual) - time.mktime(tiempo_usuario)) / 60.0
            print("--------------------------------------", diferencia_minutos)
            if diferencia_minutos <= 30.0:
                # Calculo la distancia entre el usuario que envia el SOS y el usuario actual
                R = 6371.0  # Radio de la Tierra en kilómetros

                lat1 = radians(user["latitude"])
                lon1 = radians(user["longitude"])
                lat2 = radians(u["latitude"])
                lon2 = radians(u["longitude"])

                dlon = lon2 - lon1
                dlat = lat2 - lat1

                a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))

                distance = R * c  # Distancia en kilómetros

                print(f"Distance to user {u['id_token']}: {distance} km")
                if distance <= 5.0:  # Si la distancia es menor o igual a 5 km
                    if u.get("fcm_token", None):
                        fcm_tokens_send.append(u["fcm_token"])

    def enviar_mensaje(token, titulo, cuerpo):
        mensaje = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            token=token,
        )
        respuesta = messaging.send(mensaje)
        print("Mensaje enviado:", respuesta)

    if fcm_tokens_send == []:
        return jsonify({"status": "error", "message": "No nearby users to notify, call 911"}), 445
    for token in fcm_tokens_send:
        enviar_mensaje(token, titulo, cuerpo)

    return jsonify({"status": "ok", "sos send from user": id_token}), 200

swagger = flasgger.Swagger(app, template=swagger_config)





@app.route('/get_pois_by_user_email', methods=['POST'])
def get_pois_by_user_email():
    """
    Endpoint to get all POIs created by a specific user email.
    ---
    tags:
      - POI
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "user@example.com"
    responses:
      200:
        description: POIs retrieved successfully
        schema:
          type: object
          properties:
            status:
              type: string
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  location:
                    type: object
                    properties:
                      latitude:
                        type: number
                      longitude:
                        type: number
      400:
        description: Invalid input data
    """
    body = request.get_json() 
    email = body.get('user_email', None)
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')
    if not email:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    pois = dto.get_pois_by_user_email(email, language_id=language_id)
    if not pois:
        return jsonify({"status": "error", "message": "No POIs found for this user"}), 404

    return jsonify({"status": "ok", "data": pois}), 200


@app.route('/create_poi', methods=['POST'])
def create_poi():
    body = request.get_json() 
    image = body.get('image', None)
    title = body.get('title', None)
    description = body.get('description', None)
    latitude = body.get('latitude', None)
    longitude = body.get('longitude', None)
    user_email = body.get('user_email', None)
    types = body.get('types', [])
    languages = dto.get_languages()

    if not title and not description:
        return jsonify({"status": "error", "message": "Title or description required"}), 400
    if latitude is None or longitude is None:
        return jsonify({"status": "error", "message": "Latitude and longitude required"}), 400

    url = "http://193.146.210.235:5050/generate_poi"

    payload = {
        "image": image,
        "title": title,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "types": types,
        "user_email": user_email,
        "languages": languages,
        "dev_mode": os.getenv("DB_NAME") == "rurallure-dev"
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Error creating POI"}), 500
    
    return jsonify({"status": "ok", "message": "POI queued"}), 200

    

    # dto.create_poi(image, titles, descriptions_list, latitude, longitude, types, user_email=user_email)

    # return jsonify({"title": title, "description": description}), 200



@app.route('/upload_poi_to_mongo', methods=['POST'])
def upload_poi_to_mongo():
    body = request.get_json() 
    status = body.get('status', 'ok')
    user_email = body.get('user_email', None)
    if status == 'error':
        message = body.get('message', 'Unknown error')
        titulo = "POI Inappropriate Content"
        cuerpo = f"{message}."

    else:
      image_base64 = body.get('image', None)
      titles = body.get('titles', None)
      descriptions_list = body.get('descriptions', None)
      latitude = body.get('latitude', None)
      longitude = body.get('longitude', None)
      types = body.get('types', [])
      address = body.get('address', None)
      website = body.get('website', None)
      booking = body.get('booking', None)
      minutes_duration = body.get('minutes_duration', None)
      zenodo_url = body.get('zenodo_url', None)
      is_mobility_friendly = body.get('is_mobility_friendly', None)
      opening_hours = body.get('opening_hours', None)

      

      image = utils.base64StringToJpg(image_base64)


      dto.create_poi(image, titles, descriptions_list, latitude, longitude, types, user_email=user_email, address=address, website=website, booking=booking, minutes_duration=minutes_duration, zenodo_url=zenodo_url, is_mobility_friendly=is_mobility_friendly, opening_hours=opening_hours)

      #mandamos notificacion de que se ha subido el POI
      titulo = "POI Created Successfully"
      cuerpo = "Tu punto de interés ha sido creado correctamente. ¡Gracias por contribuir!"
    try: 
      fcm_token = dto.get_user_fcm_token_by_email(user_email)
      if fcm_token: 
      
        mensaje = messaging.Message(
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            token=fcm_token,
        )
        respuesta = messaging.send(mensaje)
        print("Mensaje enviado:", respuesta)
    except Exception as e:
      return jsonify({"status": "ok", "message": "POi created, no notification sent"}), 200

    return jsonify({"status": "ok", "message": "Job Done"}), 200


@app.route('/delete_poi', methods=['POST'])
def delete_poi():
    body = request.get_json() 
    poi_id = body.get('poi_id', None)
    if not poi_id:
        return jsonify({"status": "error", "message": "Missing poi_id parameter"}), 400

    dto.delete_poi(poi_id)

    return jsonify({"status": "ok", "message": "POI deleted"}), 200





@app.route('/two_points_route', methods=['POST'])
def two_points_route():
    body = request.get_json()
    latitude1 = body.get('latitude1', None)
    longitude1 = body.get('longitude1', None)
    latitude2 = body.get('latitude2', None)
    longitude2 = body.get('longitude2', None)
    
    route = utils.get_route([latitude1, longitude1], [latitude2, longitude2], profile="foot")


    return jsonify({"status": "ok", "route": route}), 200




@app.route('/get_pois_around_a_route', methods=['POST'])
def get_pois_around_a_route():
    body = request.get_json()
    route_id = body.get('route_id', None)
    distance_km = float(body.get('distance_km', 1.0))
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')

    if not route_id:
        return jsonify({"status": "error", "message": "Missing route_id parameter"}), 400

    pois = dto.get_pois_around_a_route(route_id, distance_km, language_id)

    return jsonify({"status": "ok", "data": pois}), 200



@app.route('/create_route', methods=['POST'])
def create_route():
    body = request.get_json()
    language_id = body.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3') 
    long_description = body.get('long_description', '')
    name = body.get('name', "")
    image = body.get('image', None)
    short_description = body.get('short_description', "")
    route_type = body.get('route_type', None)
    stage_breaks = body.get('stage_breaks', [])
    poi_ids = body.get('poi_ids', [])
    owner = body.get('owner', None)
    subtype = body.get('subtype', None)

    pois_coords = []
    poi_image_ids = []
    poi_names = []

    print("Creating route with POIs:", poi_ids)

    for poi_id in poi_ids:
        poi = dto.get_poi_by_id(poi_id, language_id)
        pois_coords.append([float(poi['latitude']), float(poi['longitude'])])
        poi_names.append(poi['title'])
        if poi.get("image_id", None):
            poi_image_ids.append(poi["image_id"])


    actual_day = 1
    stages = []
    all_points = []
    total_distance = 0

    for i in range(len(pois_coords)):
        if i == 0:
            stages.append({
                "day": actual_day,
                "name": f"{poi_names[i]} - ",
                "points_of_interest": [ {"id": poi_ids[i], "distance": 0}],
            })

        else:
            points, distance = utils.get_route_with_distance(pois_coords[i-1], pois_coords[i], profile="foot")
            total_distance += distance
            for point in points:
                all_points.append(point)

            if i in stage_breaks:
                stages[-1]["points_of_interest"].append({"id": poi_ids[i], "distance": distance})
                stages[-1]["name"] += f"{poi_names[i]}"
                actual_day += 1
                stages.append({
                    "day": actual_day,
                    "name": f"{poi_names[i]} - ",
                    "points_of_interest": [ {"id": poi_ids[i], "distance": 0}],
                })
            else:
                stages[-1]["points_of_interest"].append({"id": poi_ids[i], "distance": distance})


    print("all_points:", all_points)
    locations = {
        "start": all_points[0],
        "end": all_points[-1],
        "all_points": all_points
    }
    image_id = None
    image_jpg = None

    if image:
        image_jpg = utils.base64StringToJpg(image)
    else:
        image_id = poi_image_ids[0] if poi_image_ids else None

    total_distance = round(total_distance, 2)

    route = dto.create_route(language_id, long_description, name, short_description, route_type, stages, locations, owner, subtype, total_distance, image_id = image_id, image_body=image_jpg)
    return jsonify({"status": "ok", "data": route}), 200



@app.route('/delete_route/<route_id>', methods=['DELETE'])
def delete_route(route_id):
    if not route_id:
        return jsonify({"status": "error", "message": "Missing route_id parameter"}), 400

    dto.delete_route(route_id)

    return jsonify({"status": "ok", "message": "Route deleted"}), 200























if __name__ == '__main__':
  # # generate swagger documentation
  # with app.app_context():
  #     swagger_spec = swagger.get_apispecs()
  #     # Guardar en JSON
  #     with open("swagger/swagger.json", "w", encoding="utf-8") as f:
  #         json.dump(swagger_spec, f, indent=2, ensure_ascii=False)

  #     # Guardar también en YAML (opcional)
  #     with open("swagger/swagger.yaml", "w", encoding="utf-8") as f:
  #         yaml.dump(swagger_spec, f, allow_unicode=True)

  #     print("✅ Swagger guardado en swagger.json y swagger.yaml")
  app.run(debug=True, host='127.0.0.1', port=5000)