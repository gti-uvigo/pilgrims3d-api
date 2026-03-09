from pymongo import MongoClient
import requests
from pymongo.errors import ConnectionFailure


# --- Configuración de la conexión a MongoDB con usuario y contraseña ---

MONGO_USER = "admin"
MONGO_PASS = "pln_om"
MONGO_HOST = "193.146.210.248"
MONGO_PORT = 27017
MONGO_AUTH_DB = "admin"  # Cambia si tu autenticación es en otra base

mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_AUTH_DB}"


try:
    client = MongoClient(mongo_uri)
    client.admin.command('ping')
    print("Conexión a MongoDB exitosa.")
except ConnectionFailure as e:
    print(f"Error al conectar a MongoDB: {e}")
    exit()

# Selecciona tu base de datos


def get_routes(db_name='rurallure-dev'):
    """
    Obtiene todas las rutas de la base de datos.
    """
    db = client[db_name]
    routes = db.routes.find()
    return [route for route in routes]


def get_poi_by_filter(db_name='rurallure-dev', filter={}):
    """
    Obtiene POIs de la base de datos según un filtro.
    """
    db = client[db_name]
    pois = db.pois.find(filter)
    return [poi for poi in pois]


def update_route(db_name='rurallure-dev', filter={}, update={}):
    """
    Actualiza una ruta en la base de datos según un filtro.
    """
    db = client[db_name]
    result = db.routes.update_one(filter, {'$set': update})
    return result.modified_count


def get_route_by_filter(db_name='rurallure-dev', filter={}):
    """
    Obtiene rutas de la base de datos según un filtro.
    """
    db = client[db_name]
    routes = db.routes.find(filter)
    return [route for route in routes]

def get_text_by_lang(text_list, lang_id):
    """Busca en una lista de diccionarios el que coincide con el lang_id y devuelve su texto."""
    for item in text_list:
        if item.get("language_id") == lang_id:
            return item.get("text")
    return None



if __name__ == "__main__":
    route_title = "Desde Lindoso (fácil)"
    lang = "6d68e409-c46e-4d4a-8560-f15256e9cbb3"
    route = get_route_by_filter(filter={"titles.text": route_title})[0]


    route["title"] = get_text_by_lang(route["titles"], lang)
    route["long_description"] = get_text_by_lang(route["long_descriptions"], lang)
    route["short_description"] = get_text_by_lang(route["short_descriptions"], lang)

        
    for stage in route.get("stages", []):
        pois_completos = []
        for poi_n in stage.get("points_of_interest", []):
            poi = get_poi_by_filter(filter={"id": poi_n["id"]})[0]
            poi["title"] = get_text_by_lang(poi["titles"], lang)
            poi["description"] = get_text_by_lang(poi["descriptions"], lang)
            for key in ["titles", "descriptions"]:
                if key in poi:
                    del poi[key]
            pois_completos.append(poi)
        stage["points_of_interest"] = pois_completos

    for key in ["titles", "long_descriptions", "short_descriptions", "locations", "_id"]:
        if key in route:
            del route[key]
    print(route)


    


