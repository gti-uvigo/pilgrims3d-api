import pandas as pd
import os

from .database import PostgreSQLManager
from .utils import get_logger, get_bouncing_box, haversine

logger = get_logger(__name__)

# ==========================================================
# /pois/around
# ==========================================================
def ep_pois_around(body:dict, db_manager:PostgreSQLManager):
    # Endpoint parameters:
    default_radius = 2000 # meters
    default_n_max = None # max number of points of interest to return (if none return all)
    # -----
    if "latitude" not in body or "longitude" not in body:
        return {"status": "error", "message": "Bad format. Body must have 'latitude' and 'longitude' keys"}
    latitude = body["latitude"]
    longitude = body["longitude"]

    radius = body.get("radius", default_radius)
    n_max = body.get("n_max", default_n_max)
    
    logger.info(f"Received location: {latitude}, {longitude} with radius {radius} and max number of pois {n_max}")

    bouncing_box = get_bouncing_box(latitude, longitude, radius)
    result = get_pois_in_bouncing_box(db_manager, bouncing_box)
    if result["status"] != "ok":
        return result
    pois_inside_box = result["data"]
    
    result = get_pois_around_location(pois_inside_box, radius, n_max) # Delete POIS outside the radius
    if result["status"] != "ok":
        return result

    filtered_pois = result["data"].to_dict(orient="records")

    return {"status": "ok", "pois": filtered_pois, "radius": radius, "n_max": n_max}


# ==============================================================
# /pois/near-any
# ==============================================================
def ep_pois_near_any(body:dict, db_manager:PostgreSQLManager):
    # Endpoint parameters:
    default_radius = 20000 # meters
    default_n_max = None # max number of points of interest to return (if none return all)

    if "locations" not in body:
        return {"status": "error", "message": "Key 'location' not found in request body."}
    locations = body["locations"]
    if type(locations) != list:
        return {"status": "error", "message": "Key 'locations' must be a list."}
    if len(locations) != 2:
        return {"status": "error", "message": "Key 'locations' must have 2 elements."}
    
    for loc in locations:
        if "latitude" not in loc or "longitude" not in loc:
            return {"status": "error", "message": "Bad format. Each location must have 'latitude' and 'longitude' keys."}
    
    # Location 1
    lat1 = locations[0]["latitude"]
    lon1 = locations[0]["longitude"]
    # Location 2
    lat2 = locations[1]["latitude"]
    lon2 = locations[1]["longitude"]
    # Other parameters
    radius = body.get("radius", default_radius)
    n_max = body.get("n_max", default_n_max)

    logger.info(f"Searching POIS in near ({lat1},{lon1}) and ({lat2},{lon2}) with radius {radius} and max number of pois {n_max}")

    # Get bouncing boxes
    bouncing_box1 = get_bouncing_box(lat1, lon1, radius)
    bouncing_box2 = get_bouncing_box(lat2, lon2, radius)

    # Pois near location 1
    result = get_pois_in_bouncing_box(db_manager, bouncing_box1)
    if result["status"] != "ok":
        return result
    pois_inside_box = result["data"]
    result = get_pois_around_location(pois_inside_box, radius, n_max) # Delete POIS outside the radius
    if result["status"] != "ok":
        return result
    df_pois_near_loc1 = result["data"]

    # Pois near location 2
    result = get_pois_in_bouncing_box(db_manager, bouncing_box2)
    if result["status"] != "ok":
        return result
    pois_inside_box = result["data"]
    result = get_pois_around_location(pois_inside_box, radius, n_max) # Delete POIS outside the radius
    if result["status"] != "ok":
        return result
    df_pois_near_loc2 = result["data"]

    # Merge dataframes and remove duplicates
    df_interseccion = pd.merge(df_pois_near_loc1, df_pois_near_loc2, on=['id', 'latitude', 'longitude'], how='inner')
    df_interseccion = df_interseccion.drop_duplicates()

    pois = result["data"].to_dict(orient="records")

    return {"status": "ok", "pois": pois, "radius": radius, "n_max": n_max}


# ==============================================================
# /poi/decription
# ==============================================================
def ep_poi_description(body:dict, db_manager:PostgreSQLManager):
    if "id" not in body:
        return {"status": "error", "message": "Key 'id' not found in request body."}
    poi_id = body["id"]
    
    language = "es"
    if "language" in body:  # Optional
        language = body["language"]

    logger.info(f"Getting description - POI id: {poi_id} and language: {language}")

    # Get language id
    result = get_language_id(db_manager, language)
    if result["status"] != "ok":
        return result
    lang_id = result["id"]
    # lang_name = lang_id_response["name"]
    if lang_id is None:
        return {"status": "error", "message": f"Language '{language}' not found in database."}
    
    # Get POI location
    result = get_poi_location(db_manager, poi_id)
    if result["status"] != "ok":
        return result
    latitude = result["latitude"]
    longitude = result["longitude"]

    # Get title and description
    result = get_poi_description(db_manager, poi_id, lang_id)
    if result["status"] != "ok":
        return result
    print(result)
    title = result["title"]
    description = result["description"]

    # Get image
    result = get_poi_image_file_id(db_manager, poi_id)
    if result["status"] != "ok":
        return result
    image_file_id = result["file_id"]

    result = get_image_filename(db_manager, image_file_id)
    if result["status"] != "ok":
        return result
    filename = result["filename"]

    # Get category
    result = get_category_id(db_manager, poi_id)
    if result["status"] != "ok":
        return result
    category_id = result["category_id"]
    result = get_category_name(db_manager, category_id, lang_id)
    if result["status"] != "ok":
        return result
    print(result)
    category_name = result["category_name"]

    return {"status": "ok", "id": poi_id, "language": language, "location": {"latitude": latitude, "longitude": longitude},
            "title": title, "description": description, "image": filename, "category": category_name}


# ===========================================================
# DATABASE CONSULTS
# ===========================================================
def get_pois_in_bouncing_box(db_manager:PostgreSQLManager, bouncing_box:dict):
    # Database parameters:
    table_name = "point_of_interest"
    latitude_atribute = "gps_latitude"
    longitude_atribute = "gps_longitude"
    attributes_to_select = ["id", latitude_atribute, longitude_atribute]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE {latitude_atribute} BETWEEN %s AND %s 
        AND {longitude_atribute} BETWEEN %s AND %s;
    """
    try:
        pois = db_manager.execute(query, (bouncing_box["min_latitude"], bouncing_box["max_latitude"],
                                          bouncing_box["min_longitude"], bouncing_box["max_longitude"]))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if pois is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(pois) == 0:
        return {"status": "ok", "pois": []}
    
    pois = pd.DataFrame(pois, columns=attributes_to_select)
    pois.rename(columns={latitude_atribute: "latitude", longitude_atribute: "longitude"}, inplace=True)

    return {"status": "ok", "data": pois}
    
def get_pois_around_location(pois:pd.DataFrame, radius:int, n_max:int=None):
    if n_max is not None and n_max < 0:
        return {"status": "error", "message": "n_max must be greater than or equal to 0."}
    # Add distance column
    pois["distance"] = pois.apply(lambda row: haversine(row["latitude"], row["longitude"], pois.iloc[0]["latitude"], pois.iloc[0]["longitude"]), axis=1)

    # Filter wher distance > radius
    pois = pois[pois["distance"] <= radius]

    # Remove duplicates
    pois = pois.drop_duplicates(subset=["latitude", "longitude"])

    # Sort by distance
    pois = pois.sort_values(by="distance")
    # Reset index
    pois = pois.reset_index(drop=True)

    # Limit to n_max
    if n_max is not None:
        pois = pois.head(n_max)
    
    # Drop distance column
    pois = pois.drop(columns=["distance"])
    return {"status": "ok", "data": pois}


def get_language_id(db_manager:PostgreSQLManager, language:str):
    # Database parameters:
    table_name = "languages"
    attributes_to_select = ["id", "name"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE iso_639_1_code = %s;
    """
    try:
        lang_ids = db_manager.execute(query, (language,))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if lang_ids is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(lang_ids) == 0:
        return {"status": "ok", "id": None}
    elif len(lang_ids) > 1:
        logger.warning(f"More than one language id found for {language}: {lang_ids}")
        return {"status": "error", "message": f"More than one language id found for {language}: {lang_ids}"}

    # Get the id of the first language
    lang_id = lang_ids[0][0]
    lang_name = lang_ids[0][1]
    logger.info(f"Language id for {language} ({lang_name}) is {lang_id}")

    return {"status": "ok", "id": lang_id, "name": lang_name}


def get_poi_location(db_manager:PostgreSQLManager, poi_id:int):
    # Database parameters:
    table_name = "point_of_interest"
    attributes_to_select = ["id", "gps_latitude", "gps_longitude"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE id = %s;
    """
    try:
        pois = db_manager.execute(query, (poi_id,))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if pois is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(pois) == 0:
        return {"status": "ok", "pois": []}
    elif len(pois) > 1:
        logger.warning(f"More than one POI found for id {poi_id}: {pois}")
        return {"status": "error", "message": f"More than one POI found for id {poi_id}: {pois}"}
    
    # Get the location of the first POI
    latitude = pois[0][1]
    longitude = pois[0][2]

    return {"status": "ok", "latitude": latitude, "longitude": longitude}


def get_poi_description(db_manager:PostgreSQLManager, poi_id:int, language_id:str):
    # Database parameters:
    table_name = "point_of_interest_translation"
    attributes_to_select = ["id", "title", "description"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE point_of_interest_id = %s AND language_id = %s;
    """
    try:
        pois = db_manager.execute(query, (poi_id,language_id))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if pois is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(pois) == 0:
        return {"status": "ok", "title": None, "description": None}
    elif len(pois) > 1:
        logger.warning(f"More than one POI found for id {poi_id} and language {language_id}: {pois}")
        return {"status": "error", "message": f"More than one POI found for id {poi_id} and language {language_id}: {pois}"}
    
    # Get title and description of the first POI
    title = pois[0][1]
    description = pois[0][2]

    return {"status": "ok", "title": title, "description": description}

def get_poi_image_file_id(db_manager:PostgreSQLManager, poi_id:int):
    # Database parameters:
    table_name = "image_point_of_interest"
    attributes_to_select = ["id", "file_uploaded_id"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE point_of_interest_id = %s;
    """
    try:
        pois = db_manager.execute(query, (poi_id,))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if pois is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(pois) == 0:
        return {"status": "ok", "file_uploaded_id": None}
    if len(pois) > 1:
        logger.warning(f"More than one POI found for id {poi_id}: {pois}")
        return {"status": "error", "message": f"More than one POI found for id {poi_id}: {pois}"}
    
    # Get the image file uploaded id of the first POI
    image_file_uploaded_id = pois[0][1]

    return {"status": "ok", "file_id": image_file_uploaded_id}


def get_image_filename(db_manager:PostgreSQLManager, file_id:int):
    # Database parameters:
    table_name = "file_uploaded"
    attributes_to_select = ["id", "filename"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE id = %s;
    """
    try:
        files = db_manager.execute(query, (file_id,))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if files is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(files) == 0:
        return {"status": "ok", "filename": None}
    elif len(files) > 1:
        logger.warning(f"More than one file found for id {file_id}: {files}")
        return {"status": "error", "message": f"More than one file found for id {file_id}: {files}"}
    
    
    # Get the filename of the first file
    filename = files[0][1]

    return {"status": "ok", "filename": filename}

def get_category_id(db_manager:PostgreSQLManager, poi_id:int):
    # Database parameters:
    table_name = "point_of_interest_category"
    attributes_to_select = ["category_id"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE point_of_interest_id = %s;
    """
    try:
        category_ids = db_manager.execute(query, (poi_id,))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if category_ids is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(category_ids) == 0:
        return {"status": "ok", "category_id": None}
    if len(category_ids) > 1:
        logger.warning(f"More than one category found for id {poi_id}: {category_ids}")
        return {"status": "error", "message": f"More than one POI found for id {poi_id}: {category_ids}"}
    
    # Get the category id of the first POI
    category_id = category_ids[0][0]

    return {"status": "ok", "category_id": category_id}

def get_category_name(db_manager:PostgreSQLManager, category_id:int, language_id:int):
    # Database parameters:
    table_name = "category_translation"
    attributes_to_select = ["description"]
    # -----
    query = f"""
        SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
        WHERE category_id = %s AND language_id = %s;
    """
    try:
        categories = db_manager.execute(query, (category_id, language_id))
    except ValueError as e:
        return {"status": "error", "message": e}
    
    if categories is None:
        return {"status": "error", "message": "Error al obtener los puntos de interés."}
    elif len(categories) == 0:
        return {"status": "ok", "category_name": None}
    if len(categories) > 1:
        logger.warning(f"More than one category found for id {category_id}: {categories}")
        return {"status": "error", "message": f"More than one POI found for id {category_id}: {categories}"}
    # Get the category name of the first POI
    category_name = categories[0][0]

    return {"status": "ok", "category_name": category_name}