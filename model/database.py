import sqlite3


class Database():
    def __init__(self, db_file: str):
        self.db_file = db_file
        self._connection = None

    def connect(self):
        """Establece la conexión a la base de datos."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_file)
            self._connection.row_factory = sqlite3.Row  # Para obtener resultados como diccionarios

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def execute(self, query: str, params: tuple = ()):
        """Ejecuta una consulta SQL y devuelve el cursor."""
        if self._connection is None:
            raise Exception("La base de datos no está conectada.")
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        cursor.connection.commit()
        return cursor
    
