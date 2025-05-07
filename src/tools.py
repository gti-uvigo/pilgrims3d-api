from .database import PostgreSQLManager

def list_tables(db_manager:PostgreSQLManager):
    """
    List all tables in the PostgreSQL database.
    """
    try:
        tables = db_manager.list_tables()
        return tables
    except Exception as e:
        print(f"Error al listar tablas: {e}")
        return []


def describe_table(db_manager:PostgreSQLManager, table_name:str):
    """
    Describe the attributes of a specific table in the PostgreSQL database.
    """
    try:
        attributes = db_manager.get_table_attributes(table_name)
        return attributes
    except Exception as e:
        print(f"Error al describir la tabla '{table_name}': {e}")
        return []