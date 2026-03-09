from pymongo import MongoClient
import requests
from pymongo.errors import ConnectionFailure
import statistics

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

def generate_route_graphhoper(points):
    url = "http://193.146.210.248:8989/route"
    payload = {
        "points": points,
        "profile": "foot",
        "ch.disable": True,
        "points_encoded": False,
        "elevation": True,
        "instructions": False,
        "snap_preventions": ["ferry"],
        "custom_model": {
            "speed": [
                {
                    "if": "true",
                    "limit_to": "100"
                }
            ],
            "priority": [
                {
                    "if": "road_class == MOTORWAY",
                    "multiply_by": "0"
                }
            ],
            "distance_influence": 100
        }
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:        
        print(f"Error en la solicitud: {response.text}")



def get_route_by_filter(db_name='rurallure-dev', filter={}):
    """
    Obtiene rutas de la base de datos según un filtro.
    """
    db = client[db_name]
    routes = db.routes.find(filter)
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
    Retorna el objeto result completo.
    """
    db = client[db_name]
    result = db.routes.update_one(filter, {'$set': update})
    return result


def update_poi(db_name='rurallure-dev', filter={}, update={}):
    """
    Actualiza un POI en la base de datos según un filtro.
    """
    db = client[db_name]
    result = db.pois.update_one(filter, {'$set': update})
    return result.modified_count


def calculate_difficulty_score(distance, ascend):
    """
    Calcula un score de dificultad combinando distancia y ascenso.
    Peso: 60% distancia, 40% ascenso
    """
    distance_km = distance / 1000.0
    # Normalizar: 1 punto por km, 1 punto por cada 100m de ascenso
    score = (distance_km * 0.6) + ((ascend / 100) * 0.4)
    return score


def calculate_difficulty(score, percentiles):
    """
    Calcula la dificultad basándose en el score y los percentiles.
    
    - Easy: score <= percentil 40
    - Medium: percentil 40 < score <= percentil 65
    - Hard: score > percentil 65
    """
    if score <= percentiles['p40']:
        return "easy"
    elif score <= percentiles['p65']:
        return "medium"
    else:
        return "hard"



if __name__ == "__main__":
    route_type = "50da0d69-3647-4897-9dcc-2ed9820e1648"
    routes = get_route_by_filter(filter={"route_type": route_type})

    print(f"Procesando {len(routes)} rutas...\n")

    # Primera pasada: recopilar datos de todas las rutas
    routes_data = []
    
    for route in routes:
        try:
            route_name = route.get('titles', [{}])[0].get('text', 'Sin nombre')
            
            pois_ids = []
            for stage in route.get('stages', []):
                for poi in stage.get('points_of_interest', []):
                    pois_ids.append(poi['id'])

            if not pois_ids:
                print(f"⚠️  Ruta '{route_name}': sin POIs, omitiendo.")
                continue

            coords = []
            for id in pois_ids:
                poi = get_poi_by_filter(filter={"id": id})
                if poi:
                    coords.append([poi[0]['longitude'], poi[0]['latitude']])

            if len(coords) < 2:
                print(f"⚠️  Ruta '{route_name}': coordenadas insuficientes, omitiendo.")
                continue

            res = generate_route_graphhoper(coords)

            if res and 'paths' in res and len(res['paths']) > 0:
                path_info = res['paths'][0]
                distance = path_info.get('distance', 0)  # metros
                ascend = path_info.get('ascend', 0)  # metros
                descend = path_info.get('descend', 0)  # metros
                all_points = path_info['points']['coordinates']
                
                routes_data.append({
                    'route': route,
                    'route_name': route_name,
                    'distance': distance,
                    'ascend': ascend,
                    'descend': descend,
                    'all_points': all_points
                })
                
                print(f"✓ '{route_name}': {distance/1000:.2f}km, ascenso {ascend:.0f}m")
            else:
                print(f"✗ Error al obtener ruta GraphHopper para '{route_name}'")
                
        except Exception as e:
            print(f"✗ Error procesando ruta: {e}")
            continue

    if not routes_data:
        print("\nNo se pudieron procesar rutas.")
        exit()

    # Calcular scores de dificultad para todas las rutas
    for route_data in routes_data:
        score = calculate_difficulty_score(route_data['distance'], route_data['ascend'])
        route_data['score'] = score
    
    # Calcular percentiles
    scores = [r['score'] for r in routes_data]
    scores_sorted = sorted(scores)
    
    # Calcular percentiles manualmente
    n = len(scores_sorted)
    if n >= 3:
        idx_p40 = int(n * 0.40)
        idx_p65 = int(n * 0.65)
        percentiles = {
            'p40': scores_sorted[idx_p40],
            'p65': scores_sorted[idx_p65]
        }
    elif n == 2:
        percentiles = {
            'p40': scores_sorted[0],
            'p65': scores_sorted[1]
        }
    else:
        percentiles = {
            'p40': scores_sorted[0],
            'p65': scores_sorted[0]
        }
    
    distances_km = [r['distance'] / 1000.0 for r in routes_data]
    ascends = [r['ascend'] for r in routes_data]
    
    print(f"\n{'='*60}")
    print("ESTADÍSTICAS:")
    print(f"  Distancia media: {statistics.mean(distances_km):.2f} km")
    print(f"  Ascenso medio: {statistics.mean(ascends):.0f} m")
    print(f"  Score percentil 40: {percentiles['p40']:.2f}")
    print(f"  Score percentil 65: {percentiles['p65']:.2f}")
    print(f"{'='*60}\n")

    # Segunda pasada: calcular dificultad y actualizar todas las rutas
    updated_count = 0
    difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
    
    for route_data in routes_data:
        route = route_data['route']
        route_name = route_data['route_name']
        distance = route_data['distance']
        ascend = route_data['ascend']
        all_points = route_data['all_points']
        score = route_data['score']
        
        # Calcular dificultad usando scores y percentiles
        difficulty = calculate_difficulty(score, percentiles)
        difficulty_counts[difficulty] += 1
        
        # Actualizar locations y difficulty
        if 'locations' not in route:
            route['locations'] = {}
        route['locations']['all_points'] = all_points
        
        # Buscar por ID usando route_id
        try:
            # Intentar actualizar usando route_id (el identificador real de las rutas)
            result = None
            
            if 'route_id' in route:
                result = update_route(filter={"route_id": route['route_id']}, update={
                    "locations": route['locations'],
                    "difficulty": difficulty
                })
            
            # Fallback: usar _id si route_id no funcionó
            if result and result.matched_count == 0 and '_id' in route:
                result = update_route(filter={"_id": route['_id']}, update={
                    "locations": route['locations'],
                    "difficulty": difficulty
                })
            
            if result and result.matched_count > 0:
                updated_count += 1
                status = "actualizado" if result.modified_count > 0 else "sin cambios"
                print(f"✓ '{route_name}': {difficulty.upper()} ({status}, score={score:.2f}, dist={distance/1000:.2f}km, asc={ascend:.0f}m)")
            else:
                print(f"✗ Error actualizando '{route_name}' (no se encontró el documento)")
        except Exception as e:
            print(f"✗ Error actualizando '{route_name}': {e}")

    print(f"\n{'='*60}")
    print(f"RESUMEN:")
    print(f"  Rutas actualizadas: {updated_count}/{len(routes_data)}")
    print(f"  Easy: {difficulty_counts['easy']}")
    print(f"  Medium: {difficulty_counts['medium']}")
    print(f"  Hard: {difficulty_counts['hard']}")
    print(f"{'='*60}")

