import psycopg
import os
import pandas as pd

class PostgreSQLManager:

    def __init__(self, config:dict):
        self.host = config.get("host")
        self.port = config.get("port")
        self.user = config.get("user")
        self.db_name = config.get("db_name")
        password_var = config.get("password_var")
        self.password = os.getenv(password_var)
        if not self.password:
            raise ValueError(f"La variable de entorno '{password_var}' no está definida o está vacía.")
        
        self.connection = self.connect()
        if self.connection:
            print("Conexión exitosa a la base de datos.")
        else:
            print("Error al conectar a la base de datos.")
    
    # ====================================
    # Connection and disconnection
    # ====================================
    def connect(self):
        try:
            conn = psycopg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.db_name
            )
            return conn
        except psycopg.Error as e:
            print(f"Error al conectar con la base de datos: {e}")
            return None
        
    def disconnect(self):
        if self.connection:
            self.connection.close()
            print("Conexión cerrada exitosamente.")
    
    # ====================================
    # Table management
    # ====================================
    def list_tables(self):
        if not self.connection:
            print("No hay conexión a la base de datos.")
            return []
        try:
            with self.connection.cursor() as cursor:
                #cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                cursor.execute("""SELECT relname FROM pg_class WHERE relkind='r'
                  AND relname !~ '^(pg_|sql_)';""")
                tables = cursor.fetchall()
                return [table[0] for table in tables]
        except psycopg.Error as e:
            print(f"Error al obtener la lista de tablas: {e}")
            return []
    
    def describe_table(self, table_name: str):
        if not self.connection:
            print("No hay conexión a la base de datos.")
            return []
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT attname AS col, atttypid::regtype AS datatype
                    FROM pg_attribute
                    WHERE attrelid = %s::regclass 
                    AND attnum > 0
                    AND NOT attisdropped
                    ORDER BY attnum;""", 
                    (table_name,))
                attributes = cursor.fetchall()
                return attributes
        except psycopg.Error as e:
            print(f"Error al obtener atributos de la tabla '{table_name}': {e}")
            return []
    
    def execute(self, query:str, params:tuple=None):
        if not self.connection:
            print("No hay conexión a la base de datos.")
            raise ValueError("No hay conexión a la base de datos.")
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return cursor.fetchall()
        except psycopg.Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            raise ValueError(f"Error al ejecutar la consulta: {e}")

    # =====================================
    # Data management
    # =====================================
    def get_points_of_interest(
            self,
            max_latitude: float,
            min_latitude: float,
            max_longitude: float,
            min_longitude: float,
    ):
        table_name = "point_of_interest"
        latitude_atribute = "gps_latitude"
        longitude_atribute = "gps_longitude"
        attributes_to_select = ["id", latitude_atribute, longitude_atribute]

        if not self.connection:
            return {"status": "error", "message": "No hay conexión a la base de datos."}

        try:
            with self.connection.cursor() as cursor:
                query = f"""
                    SELECT {PostgreSQLManager.str_select_atributes(attributes_to_select)} FROM {table_name} 
                    WHERE {latitude_atribute} BETWEEN %s AND %s 
                    AND {longitude_atribute} BETWEEN %s AND %s;
                """
                cursor.execute(query, (min_latitude, max_latitude, min_longitude, max_longitude))
                results = cursor.fetchall()
                results = pd.DataFrame(results, columns=attributes_to_select)
                # Convert latitude and longitude to float
                # results[latitude_atribute] = results[latitude_atribute].astype(float)
                # results[longitude_atribute] = results[longitude_atribute].astype(float)
                # Change gps_latitude to latitude and gps_longitude to longitude
                results.rename(columns={latitude_atribute: "latitude", longitude_atribute: "longitude"}, inplace=True)
                # Results: df with "id", "latitude" and "longitude"
                return {"status": "ok", "data": results}
        except psycopg.Error as e:
            return {"status": "error", "message": f"Error al obtener los puntos de interés: {e}"}

    def get_routes(self,routes_id:list):
        """
        Get all available routes in the API.
        """
        try:
            routes = []
            if not routes_id: routes_id = ['50da0d69-3647-4897-9dcc-2ed9820e1648', '946f21c8-4b83-4808-bf49-7e7e3e803d12']
            routes_id = ', '.join(f"'{id_}'" for id_ in (', '.join(map(str, routes_id))).split(', '))  # Add quotes around each id 
            with self.connection.cursor() as cursor:
                query = f"SELECT * FROM trip t JOIN trip_pilgrim tp ON t.id = tp.id WHERE t.partnership_id IN ({routes_id});"
                cursor.execute(query)
                results = cursor.fetchall()
                for row in results:
                    route = {
                        "id": str(row[0]),
                        "name": str(row[12]),
                        "start_gps_latitude": float(row[15]),
                        "start_gps_longitude": float(row[16]),
                        "end_gps_latitude": float(row[17]),
                        "end_gps_longitude": float(row[18]),
                    }
                    routes.append(route)
            return {"status": "ok", "data": routes}
        except psycopg.Error as e:
            return {"status": "error", "message": f"Error al obtener las rutas: {e}"}
        
    def get_route_types(self):
        """
        Get all available route types in the API.
        """
        try:
            route_types = []
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id, description  FROM partnership;")
                results = cursor.fetchall()
                for row in results:
                    route_type = {
                        "id": str(row[0]),
                        "name": str(row[1]),
                    }
                    route_types.append(route_type)
            return {"status": "ok", "data": route_types}
        except psycopg.Error as e:
            return {"status": "error", "message": f"Error al obtener los tipos de ruta: {e}"}

    # =====================================
    # Helper methods
    # =====================================
    def str_select_atributes(atributes:list) -> str:
        """
        Convert a list of attributes to a string for SQL SELECT statement.
        """
        return ", ".join(atributes)