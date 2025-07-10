import db.dto as dto
from flask import Flask, jsonify, request
from flask_cors import CORS
from utils import get_route
import flasgger

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


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
    language_id = request.args.get('language_id', '6d68e409-c46e-4d4a-8560-f15256e9cbb3')

    print(f"Received route_type: {route_type}, type: {tipe}, language_id: {language_id}")

    result = dto.get_routes_descriptions_by_type(route_type=route_type, type=tipe, language_id=language_id)
    if not result:
        return jsonify({"status": "error", "message": "Route not found"}), 404

    return jsonify({"status": "ok", "data": result}), 200



@app.route('/route_stages/<route_id>/<language_id>', methods=['GET'])
def function_get_route_stages(route_id, language_id):
    """
    Endpoint to get all stages of a specific route.
    ---
    tags:
      - Routes
    parameters:
      - in: path
        name: route_id
        type: string
        required: true
        description: ID de la ruta
      - in: path
        name: language_id
        type: string
        required: true
        description: ID del idioma
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

    return jsonify({"status": "ok", "data": result}), 200



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
    if not body or "start_points" not in body:
        return jsonify({"status": "error", "message": "Invalid request body"}), 400
    
    route_start = body.get("start_points")
    all_route = dto.get_route_locations(route_id)

    if not all_route:
        return jsonify({"status": "error", "message": "Route locations not found"}), 404

    route_to_locations = get_route(route_start, [all_route[0]["locations"]["all_points"][0][1], all_route[0]["locations"]["all_points"][0][0]], profile="foot")

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

swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Rurallure API",
        "description": "Documentación de la API de rutas y puntos de interés de Rurallure.",
        "version": "1.0.0"
    }
}


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





swagger = flasgger.Swagger(app, template=swagger_config)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)