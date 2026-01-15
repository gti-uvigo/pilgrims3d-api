from db.dao import delete_method, get_method, post_method, get_image_gridfs, update_method, upload_image_gridfs
import uuid
import time
from bson import ObjectId


def get_text_by_lang(text_list, lang_id):
    """Busca en una lista de diccionarios el que coincide con el lang_id y devuelve su texto."""
    for item in text_list:
        if item.get("language_id") == lang_id:
            return item.get("text")
    return None


def get_routes_descriptions_by_type(route_type: str, type: str = "featured", language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene las rutas filtradas por tipo de ruta y, opcionalmente, por idioma.
    :param route_type: Tipo de ruta a filtrar.
    :param language_id: ID del idioma para filtrar las rutas (por defecto es un ID específico).
    :return: Lista de rutas que coinciden con el tipo y el idioma especificados.
    """
    if not route_type:
        raise ValueError("El tipo de ruta no puede ser vacío.")
    routes = get_method("routes", {"route_type": route_type, "type": type, "visibility": "public"}, many=True)
    for route in routes:
        route["title"] = get_text_by_lang(route.get("titles", []), language_id)
        route["short_description"] = get_text_by_lang(route.get("short_descriptions", []), language_id)
        route["long_description"] = get_text_by_lang(route.get("long_descriptions", []), language_id)
        for key in ["titles", "short_descriptions", "long_descriptions", "_id", "stages", "locations"]:
            if key in route:
                del route[key]
    return routes


def get_route_stages(route_id: str):
    """
    Obtiene todas las etapas de las rutas disponibles.
    
    :return: Lista de etapas de rutas.
    """
    route_stages = get_method("routes", {"route_id": route_id}, many=False)
    
    if "stages" not in route_stages:
        return {"stages": []}
    return route_stages["stages"]



def create_route_type(name: str):
    """
    Crea un nuevo tipo de ruta en la base de datos.
    
    :param name: Nombre del tipo de ruta a crear.
    :return: Resultado de la creación del tipo de ruta.
    """
    route_type_data = {
        "id": str(uuid.uuid4()),
        "name": name,
        "subtypes": [{"name": "featured"}]
    }
    result_id = post_method("route_types", route_type_data)
    result = get_method("route_types", {"_id": ObjectId(result_id)})
    del result["_id"]

    return result


def get_route_locations(route_id: str):
    """
    Obtiene todas las ubicaciones de las rutas disponibles.
    
    :return: Lista de ubicaciones de rutas.
    """
    route_locations = get_method("routes", {"route_id": route_id}, many=True)
    for location in route_locations:
        keys_to_delete = [key for key in location if key != "locations"]
        for key in keys_to_delete:
            del location[key]
    return route_locations



def get_poi_by_id(poi_id: str, language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene un punto de interés (POI) por su ID.
    
    :param poi_id: ID del punto de interés a buscar.
    :return: Punto de interés encontrado o None si no se encuentra.
    """
    print("getting POI ID:", poi_id)
    poi = get_method("pois", {"id": poi_id})
    
    poi["title"] = get_text_by_lang(poi.get("titles", []), language_id)
    poi["description"] = get_text_by_lang(poi.get("descriptions", []), language_id)
    if poi:
        for key in ["_id"]:
            if key in poi:
                del poi[key]
    return poi

def update_poi(poi:dict):
    """
    Actualiza un punto de interés (POI) por su ID.
    
    :param poi: Diccionario con los datos del POI a actualizar.
    :return: Resultado de la actualización del POI.
    """
    not_updated_poi = get_method("pois", {"id": poi["id"]})

    for key in ["descriptions", "titles"]:
        if key in poi and key in not_updated_poi:
            updated_lang_ids = {item["language_id"] for item in poi[key]}      
            for lang_item in not_updated_poi[key]:
                if lang_item["language_id"] not in updated_lang_ids:
                    poi[key].append(lang_item)

    result = update_method("pois", {"id": poi["id"]}, {"$set": poi})
    return result



def get_pois_with_zenodo_url(language_id):
    """
    Obtiene todos los puntos de interés (POIs) que tienen una URL de Zenodo.
    
    :return: Lista de POIs con URL de Zenodo.
    """
    pois = get_method("pois", {"zenodo_url": {"$exists": True, "$ne": ""}}, many=True)
    
    for poi in pois:
        poi["title"] = get_text_by_lang(poi.get("titles", []), language_id)
        poi["description"] = get_text_by_lang(poi.get("descriptions", []), language_id)
        for key in ["_id", "titles", "descriptions"]:
            if key in poi:
                del poi[key]
    return pois



def get_languages():
    """
    Obtiene todos los idiomas disponibles.
    
    :return: Lista de idiomas.
    """
    languages = get_method("languages", {}, many=True)
    for language in languages:
        for key in ["_id"]:
            if key in language:
                del language[key]
    return languages



def get_route_types():
    """
    Obtiene todos los tipos de rutas disponibles.
    
    :return: Lista de tipos de rutas.
    """
    route_types =  get_method("route_types", {}, many=True)
    for route_type in route_types:
        for key in ["_id"]:
            if key in route_type:
                del route_type[key]
    return route_types

def get_pois_types(language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene todos los tipos de puntos de interés (POIs) disponibles.
    
    :return: Lista de tipos de POIs.
    """
    types = []
    pois_types = get_method("pois_categories", {}, many=True)
    for pois_type in pois_types:
        for language in pois_type["languages"]:
            if language["language_id"] == language_id:
                text = language["name"]
                types.append({"id": pois_type["id"], "text": text})
    return types

def get_image_by_id(image_id: str):
    """
    Obtiene una imagen por su ID.
    
    :param image_id: ID de la imagen a buscar.
    :return: Imagen encontrada o None si no se encuentra.
    """
    image = get_image_gridfs(image_id)
    return image



def get_all_pois():
    """
    Obtiene todos los puntos de interés (POIs) disponibles.
    
    :return: Lista de POIs.
    """
    pois = get_method("pois", {}, many=True)
    for poi in pois:
        for key in ["_id", "titles", "descriptions", "address", "website", "booking", "minutes_duration", "rating", "planner_priority", "image_id"]:
            if key in poi:
                del poi[key]
    return pois


def get_all_routes_by_route_type(route_type: str, language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene todas las rutas filtradas por tipo de ruta.
    
    :param route_type: Tipo de ruta a filtrar.
    :return: Lista de rutas que coinciden con el tipo especificado.
    """
    if not route_type:
        raise ValueError("El tipo de ruta no puede ser vacío.")
    routes = get_method("routes", {"route_type": route_type, "type": { "$nin": ["deactivated", "pilgrim"] }}, many=True)
    for route in routes:
        route["title"] = get_text_by_lang(route.get("titles", []), language_id)
        route["route"] = route['locations']['all_points']
        for key in ["_id", "titles", "short_descriptions", "long_descriptions", "locations", "updated_at", "owner_id", "image_id", "visibility", "distance", "type", "ratings"]:
            if key in route:
                del route[key]
    return routes




def create_poi(image, titles, descriptions, latitude, longitude, types, user_email, address = None, website = None, booking = None, minutes_duration = None, rating = None, planner_priority = None, zenodo_url = None, is_mobility_friendly = None, opening_hours = None):
    """
    Crea un nuevo punto de interés (POI) en la base de datos.
    
    :param image: Imagen del POI.
    :param titles: Lista de títulos del POI en diferentes idiomas.
    :param descriptions: Lista de descripciones del POI en diferentes idiomas.
    :param latitude: Latitud del POI.
    :param longitude: Longitud del POI.
    :param types: Tipos o categorías del POI.
    :param address: Dirección del POI (opcional).
    :param website: Sitio web del POI (opcional).
    :param booking: Información de reserva del POI (opcional).
    :param minutes_duration: Duración en minutos para visitar el POI (opcional).
    :param rating: Calificación del POI (opcional).
    :param planner_priority: Prioridad en el planificador para el POI (opcional).
    :param zenodo_url: URL de Zenodo para el POI (opcional).
    :param is_mobility_friendly: Indica si el POI es accesible para personas con movilidad reducida (opcional).
    :param opening_hours: Horario de apertura del POI (opcional).
    :return: Resultado de la creación del POI.
    """
    # generamos un uuid para la imagen
    image_id = str(uuid.uuid4())

    # guardamos la imagen en la base de datos
    upload_image_gridfs(image, image_id=image_id, metadatos={"contentType": "image/jpeg"})
    

    poi_data = {
        "id": str(uuid.uuid4()),
        "titles": titles,
        "descriptions": descriptions,
        "latitude": latitude,
        "longitude": longitude,
        "types": types,
        "address": address,
        "website": website,
        "booking": booking,
        "minutes_duration": minutes_duration,
        "rating": rating,
        "planner_priority": planner_priority,
        "image_id": image_id,
        "owner": user_email,
        "zenodo_url": zenodo_url,
        "is_mobility_friendly": is_mobility_friendly,
        "opening_hours": opening_hours,
    }
    result = post_method("pois", poi_data)
    return result


def delete_poi(poi_id: str):
    """
    Elimina un punto de interés (POI) por su ID.
    
    :param poi_id: ID del punto de interés a eliminar.
    :return: Resultado de la eliminación del POI.
    """
    result = delete_method("pois", {"id": poi_id})
    return result



def get_user_by_id(id_token: str):
    """
    Obtiene un usuario por su ID.
    
    :param user_id: ID del usuario a buscar.
    :return: Usuario encontrado o None si no se encuentra.
    """
    user = get_method("users", {"id_token": id_token})
    if user:
        for key in ["_id"]:
            if key in user:
                del user[key]
    return user


def register_user(fcm_token: str, id_token: str, email: str, latitude: str = None, longitude: str = None, timestamp: str = None):
    """
    Registra un nuevo usuario en la base de datos.
    
    :param id_token: ID del usuario.
    :param email: Email del usuario.
    :param name: Nombre del usuario (opcional).
    :return: Resultado del registro del usuario.
    """
    user_data = {
        "id_token": id_token,
        "email": email,
    }
    if fcm_token is not None:
        user_data["fcm_token"] = fcm_token
    if latitude is not None:
        user_data["latitude"] = latitude
    if longitude is not None:
        user_data["longitude"] = longitude
    if timestamp is not None:
        user_data["last_active"] = timestamp
    result = post_method("users", user_data)
    return result

def update_user(fcm_token: str, id_token: str, latitude: str, longitude: str, email: str = None, timestamp: str = None):
    """
    Actualiza la información de un usuario.
    
    :param id_token: ID del usuario a actualizar.
    :param name: Nuevo nombre del usuario (opcional).
    :param email: Nuevo email del usuario (opcional).
    :return: Resultado de la actualización del usuario.
    """
    update_data = {}
    if latitude is not None:
        update_data["latitude"] = latitude
    if longitude is not None:
        update_data["longitude"] = longitude
    if timestamp is not None:
        update_data["last_active"] = timestamp
    if fcm_token is not None:
        update_data["fcm_token"] = fcm_token


    result = update_method("users", {"id_token": id_token}, {"$set": update_data})
    return result


def get_all_users():    
    """
    Obtiene todos los usuarios disponibles.
    
    :return: Lista de usuarios.
    """
    users = get_method("users", {}, many=True)
    for user in users:
        for key in ["_id"]:
            if key in user:
                del user[key]
    return users



def get_pois_by_user_email(user_email: str, language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene todos los puntos de interés (POIs) creados por un usuario específico.
    
    :param user_email: Email del usuario cuyos POIs se desean obtener.
    :return: Lista de POIs creados por el usuario.
    """

    super_admin_emails = ["3dbigdataspace@gti.uvigo.es"]

    if not user_email:
        raise ValueError("El email del usuario no puede ser vacío.")
    
    if user_email in super_admin_emails:
        pois = get_method("pois", {"owner": {"$exists": True}}, many=True)
    else:
        pois = get_method("pois", {"owner": user_email}, many=True)
    for poi in pois:
        poi["title"] = get_text_by_lang(poi.get("titles", []), language_id)
        poi["description"] = get_text_by_lang(poi.get("descriptions", []), language_id)
        for key in ["_id"]:
            if key in poi:
                del poi[key]
    return pois



def get_user_fcm_token_by_email(email: str):
    """
    Obtiene el fcm_token de un usuario por su email.

    :param email: Email del usuario a buscar.
    :return: fcm_token del usuario encontrado o None si no se encuentra.
    """
    user = get_method("users", {"email": email})
    print("User found for FCM token:", user)
    if user != [] and user is not None:
        return user.get("fcm_token")
    return None


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos usando la fórmula de Haversine.
    """
    from math import radians, sin, cos, sqrt, atan2

    R = 6371.0  # Radio de la Tierra en kilómetros
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distancia = R * c
    return distancia

def get_pois_around_a_route(route_id, distance_km, language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene todos los puntos de interés (POIs) alrededor de una ruta específica dentro de una distancia dada.
    Excluye los POIs que ya están dentro de la ruta original (en stages o en pois).

    :param route_id: ID de la ruta.
    :param distance_km: Distancia en kilómetros para buscar POIs alrededor de la ruta.
    :return: Lista de POIs alrededor de la ruta (excluyendo los que están dentro de la ruta).
    """
    route = get_method("routes", {"route_id": route_id}, many=False)
    if not route or "locations" not in route or "all_points" not in route["locations"]:
        return []

    route_points = route["locations"]["all_points"]
    
    # Obtener los POIs que están dentro de la ruta (para excluirlos después)
    pois_in_route = set()
    
    # Agregar POIs del campo "pois" (si existe)
    if "pois" in route:
        pois_in_route.update(route["pois"])
    
    # Agregar POIs de los stages
    if "stages" in route:
        for stage in route["stages"]:
            if "points_of_interest" in stage:
                for poi in stage["points_of_interest"]:
                    if "id" in poi:
                        pois_in_route.add(poi["id"])
    
    pois = get_method("pois", {}, many=True)
    pois_around_route = []

    for poi in pois:
        try:
            # Excluir POIs que ya están en la ruta
            if "id" in poi and poi["id"] in pois_in_route:
                continue

            del poi["_id"]
            poi["title"] = get_text_by_lang(poi.get("titles", []), language_id)
            poi["description"] = get_text_by_lang(poi.get("descriptions", []), language_id)
            poi_lat = float(poi['latitude'])
            poi_lon = float(poi['longitude'])
            for point in route_points[::30]:
                route_lat = point[1]
                route_lon = point[0]
                distance = calcular_distancia_km(poi_lat, poi_lon, route_lat, route_lon)
                if distance <= distance_km:
                    pois_around_route.append(poi)
                    break
        except (KeyError, ValueError):
            continue

    return pois_around_route



def get_pois_in_a_region(north, south, east, west, language_id: str = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"):
    """
    Obtiene todos los puntos de interés (POIs) dentro de una región definida por límites geográficos.

    :param north: Latitud norte del límite.
    :param south: Latitud sur del límite.
    :param east: Longitud este del límite.
    :param west: Longitud oeste del límite.
    :return: Lista de POIs dentro de la región especificada.
    """
    query = {
    "latitude": {"$gte": south, "$lte": north},
    "longitude": {"$gte": west, "$lte": east}
    }
    pois = get_method("pois", query, many=True)
    for poi in pois:
        poi["title"] = get_text_by_lang(poi.get("titles", []), language_id)
        poi["description"] = get_text_by_lang(poi.get("descriptions", []), language_id)
        for key in ["_id"]:
            if key in poi:
                del poi[key]
    return pois



def create_route(language_id, long_description, name, short_description, route_type, stages, locations, owner, subtype, total_distance, image_id=None, image_body=None):
    """
    Crea una nueva ruta en la base de datos.
    
    :param route_data: Diccionario con los datos de la ruta a crear.
    :return: Resultado de la creación de la ruta.
    """
    if image_body is not None:
        image_id = str(uuid.uuid4())
        upload_image_gridfs(image_body, image_id=image_id, metadatos={"contentType": "image/jpeg"})


    route_data = {
        "route_id": str(uuid.uuid4()),
        "route_type": route_type,
        "titles": [{"language_id": language_id, "text": name}],
        "short_descriptions": [{"language_id": language_id, "text": short_description}],
        "long_descriptions": [{"language_id": language_id, "text": long_description}],
        "updated_at": time.strftime("%Y-%m-%d"),
        "owner_id": owner,
        "type": subtype,
        "image_id": image_id,
        "visibility": "public",
        "distance": total_distance,
        "stages": stages,
        "locations": locations,
        "ratings": {"average": 0, "count": 0},
    }
    result = post_method("routes", route_data)
    return result


def delete_route(route_id: str):
    """
    Elimina una ruta por su ID.
    
    :param route_id: ID de la ruta a eliminar.
    :return: Resultado de la eliminación de la ruta.
    """
    result = delete_method("routes", {"route_id": route_id})
    return result


###########Ratings#############


# añadimo el score a la colecction ratings
def rate_poi(user_id:str, poi_id: str, score: int):
    """
    Añade una valoración a un punto de interés (POI) por parte de un usuario.
    
    :param user_id: ID del usuario que realiza la valoración.
    :param poi_id: ID del punto de interés a valorar.
    :param score: Puntuación otorgada al POI.
    :return: Resultado de la creación de la valoración.
    """
    rating_data = {
        "user_id": user_id,
        "poi_id": poi_id,
        "score": score,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    #compruebo si el usuario ya ha valorado el POI
    existing_rating = get_method("ratings", {"user_id": user_id, "poi_id": poi_id})
    if existing_rating:
        #si ya ha valorado, actualizo la valoración
        result = update_method("ratings", {"user_id": user_id, "poi_id": poi_id}, {"$set": {"score": score, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}})
    else:
        result = post_method("ratings", rating_data)

    # actualizar la valoración media del POI
    poi = get_method("pois", {"id": poi_id})
    ratings = get_poi_ratings(poi_id)
    total_score = sum([rating["score"] for rating in ratings])
    average_score = total_score / len(ratings) if ratings else 0
    poi["rating"] = {
        "score": average_score,
        "user_ratings_total": len(ratings)
    }
    update_method("pois", {"id": poi_id}, {"$set": {"rating": poi["rating"]}})
    return poi["rating"]


def get_poi_ratings(poi_id: str):
    """
    Obtiene todas las valoraciones de un punto de interés (POI).
    
    :param poi_id: ID del punto de interés cuyas valoraciones se desean obtener.
    :return: Lista de valoraciones del POI.
    """
    ratings = get_method("ratings", {"poi_id": poi_id}, many=True)
    for rating in ratings:
        for key in ["_id"]:
            if key in rating:
                del rating[key]
    return ratings

def get_user_rating_for_poi(user_id: str, poi_id: str):
    """
    Obtiene la valoración de un usuario específico para un punto de interés (POI).
    
    :param user_id: ID del usuario.
    :param poi_id: ID del punto de interés.
    :return: Valoración del usuario para el POI o None si no se encuentra.
    """
    rating = get_method("ratings", {"user_id": user_id, "poi_id": poi_id})
    if rating:
        for key in ["_id"]:
            if key in rating:
                del rating[key]
        rating = rating["score"]
    else:
        rating = None 
    return rating