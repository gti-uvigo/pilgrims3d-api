import os
from pymongo import MongoClient
from gridfs import GridFSBucket
from bson import ObjectId
from pymongo.errors import ConnectionFailure
import uuid


# --- Configuración de la conexión a MongoDB ---
MONGO_USER = "admin"
MONGO_PASS = "pln_om"
MONGO_HOST = "193.146.210.248"
MONGO_PORT = 27017
MONGO_AUTH_DB = "admin"
DB_NAME = "rurallure-dev"

mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_AUTH_DB}"

try:
    client = MongoClient(mongo_uri)
    client.admin.command('ping')
    print("✅ Conexión a MongoDB exitosa.")
except ConnectionFailure as e:
    print(f"❌ Error al conectar a MongoDB: {e}")
    exit()

db = client[DB_NAME]
fs_bucket = GridFSBucket(db)


def get_route_by_filter(db_name='rurallure-dev', filter={}):
    """
    Obtiene rutas de la base de datos según un filtro.
    """
    try:
        db = client[db_name]
        collection = db.routes
        routes = list(collection.find(filter))
        print(f"✅ Rutas obtenidas: {len(routes)}")
        return routes
    except Exception as e:
        print(f"❌ Error al obtener rutas: {e}")
        raise

def update_route(filter, update):
    """
    Actualiza rutas en la base de datos según un filtro.
    """
    try:
        collection = db.routes
        result = collection.update_many(filter, update)
        print(f"✅ Rutas actualizadas: {result.modified_count}")
        return result.modified_count
    except Exception as e:
        print(f"❌ Error al actualizar rutas: {e}")
        raise



def upload_audio(file_path, filename, metadata=None):
    """
    Sube un archivo de audio a MongoDB usando GridFS con metadata personalizada.
    
    Args:
        file_path (str): Ruta al archivo de audio local
        filename (str): Nombre con el que se guardará el archivo en la base de datos
        metadata (dict): Diccionario con metadata personalizada
    
    Returns:
        ObjectId: ID del archivo subido
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo {file_path} no existe")
        
        # Metadata por defecto si no se proporciona
        if metadata is None:
            metadata = {}
        
        # Leer el archivo y subirlo
        with open(file_path, 'rb') as audio_file:
            file_id = fs_bucket.upload_from_stream(
                filename,
                audio_file,
                metadata=metadata
            )
        
        print(f"✅ Audio guardado con éxito con ID: {file_id}")
        return file_id
        
    except Exception as e:
        print(f"❌ Error al subir el audio: {e}")
        raise


def download_audio(file_id, output_path):
    """
    Descarga un archivo de audio desde MongoDB usando GridFS.
    
    Args:
        file_id (ObjectId o str): ID del archivo en GridFS
        output_path (str): Ruta donde se guardará el archivo
    """
    try:
        # Convertir a ObjectId si es string
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        
        # Descargar el archivo
        with open(output_path, 'wb') as output_file:
            fs_bucket.download_to_stream(file_id, output_file)
        
        print(f"✅ Audio descargado con éxito en: {output_path}")
        
    except Exception as e:
        print(f"❌ Error al descargar el audio: {e}")
        raise


def get_audio_info(file_id):
    """
    Obtiene la información y metadata de un archivo de audio.
    
    Args:
        file_id (ObjectId o str): ID del archivo en GridFS
    
    Returns:
        dict: Información del archivo incluyendo metadata
    """
    try:
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        
        # Obtener información del archivo
        file_info = db.fs.files.find_one({"_id": file_id})
        
        if file_info:
            print(f"📄 Información del archivo:")
            print(f"   - Nombre: {file_info.get('filename')}")
            print(f"   - Tamaño: {file_info.get('length')} bytes")
            print(f"   - Fecha de subida: {file_info.get('uploadDate')}")
            print(f"   - Metadata: {file_info.get('metadata', {})}")
            return file_info
        else:
            print(f"❌ No se encontró el archivo con ID: {file_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error al obtener información del audio: {e}")
        raise


def list_all_audios():
    """
    Lista solo los archivos de audio en GridFS (filtra por extensiones de audio).
    """
    try:
        # Extensiones de audio comunes
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma']
        
        # Crear un filtro regex para buscar archivos con extensiones de audio
        audio_filter = {
            "filename": {
                "$regex": f"({'|'.join([ext.replace('.', r'\.') + '$' for ext in audio_extensions])})",
                "$options": "i"  # case insensitive
            }
        }
        
        files = db.fs.files.find(audio_filter)
        
        print("🎵 Archivos de audio en GridFS:")
        count = 0
        for file_info in files:
            count += 1
            print(f"\n  ID: {file_info['_id']}")
            print(f"  Nombre: {file_info['filename']}")
            print(f"  Tamaño: {file_info['length']} bytes")
            print(f"  Fecha: {file_info.get('uploadDate')}")
            print(f"  Metadata: {file_info.get('metadata', {})}")
        
        print(f"\n📊 Total de audios encontrados: {count}")
        return count
            
    except Exception as e:
        print(f"❌ Error al listar audios: {e}")
        raise


def get_audios_by_metadata(filter_metadata):
    """
    Obtiene archivos de audio filtrados por metadata específica.
    
    Args:
        filter_metadata (dict): Filtro para la metadata (ej: {"route_id": "123"})
    
    Returns:
        list: Lista de archivos que coinciden con el filtro
    """
    try:
        # Construir el filtro para buscar en metadata
        query = {}
        for key, value in filter_metadata.items():
            query[f"metadata.{key}"] = value
        
        # Filtrar también por extensiones de audio
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma']
        query["filename"] = {
            "$regex": f"({'|'.join([ext.replace('.', r'\.') + '$' for ext in audio_extensions])})",
            "$options": "i"
        }
        
        files = db.fs.files.find(query)
        
        results = []
        print(f"🔍 Buscando audios con metadata: {filter_metadata}")
        print("─" * 60)
        
        for file_info in files:
            results.append(file_info)
            print(f"\n  ID: {file_info['_id']}")
            print(f"  Nombre: {file_info['filename']}")
            print(f"  Tamaño: {file_info['length']} bytes")
            print(f"  Metadata: {file_info.get('metadata', {})}")
        
        print(f"\n📊 Total encontrados: {len(results)}")
        return results
            
    except Exception as e:
        print(f"❌ Error al buscar audios: {e}")
        raise


def delete_audio(file_id):
    """
    Elimina un archivo de audio de GridFS.
    
    Args:
        file_id (ObjectId o str): ID del archivo a eliminar
    """
    try:
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        
        fs_bucket.delete(file_id)
        print(f"✅ Audio eliminado con éxito")
        
    except Exception as e:
        print(f"❌ Error al eliminar el audio: {e}")
        raise


# Ejemplo de uso
if __name__ == "__main__":
    # 1. Definir metadata personalizada

    route_id = "b9bcd4aa-b80b-4414-8b57-003c9c39dff8"
    # generamos un ID único para el audio (puedes usar cualquier método para generar este ID, aquí solo es un ejemplo)
    audio_id = uuid.uuid4().hex
    custom_metadata = {
        "audio_id": audio_id,  # ID único para el audio
        "title": "El Camino del Vino y el Silencio",
        "route_id": route_id,
    }
    
    # 2. Subir el audio con metadata
    # Reemplaza con la ruta real de tu archivo de audio
    audio_path = "./lindoso_easy.mp3"
    
    if os.path.exists(audio_path):
        file_id = upload_audio(
            file_path=audio_path,
            filename="lindoso_easy.mp3",
            metadata=custom_metadata
        )

        route = get_route_by_filter(filter={"route_id": route_id})
        update_route(
            filter={"route_id": route_id},
            update={"$set": {"audio_id": audio_id}}
        )
        
        # 3. Obtener información del archivo subido
        get_audio_info(file_id)
    else:
        print(f"⚠️  El archivo {audio_path} no existe.")
        print("\n📋 Funciones disponibles:")
        print("   - upload_audio(file_path, filename, metadata)")
        print("   - download_audio(file_id, output_path)")
        print("   - get_audio_info(file_id)")
        print("   - list_all_audios()  # Lista solo audios, no imágenes")
        print("   - get_audios_by_metadata(filter)  # Filtra por metadata")
        print("   - delete_audio(file_id)")
        print("\n💡 Ejemplos:")
        print("   # Listar todos los audios")
        print("   list_all_audios()")
        print("\n   # Buscar audios de una ruta específica")
        print('   get_audios_by_metadata({"route_id": "b9bcd4aa-b80b-4414-8b57-003c9c39dff8"})')
    # get_audios_by_metadata({})
    # delete_audio('69aebbe0fb3dff0a9be0429f')
