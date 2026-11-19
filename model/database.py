"""Conexión a la base de datos SQLite.

QUIÉN DECIDE CUÁNDO SE GUARDA

`execute` ya no hace `commit()`. La conexión se abre con `isolation_level=None`,
que apaga las transacciones implícitas del driver de Python: una sentencia
suelta se guarda sola, y cuando hace falta que varias escrituras sean una sola
operación, se envuelven con `transaccion()`.

    with db.transaccion():
        medico_repo.registrar(medico)
        cita_repo.registrar(cita)
    # un solo COMMIT al salir; ROLLBACK completo si algo revienta

`transaccion()` se puede anidar: la externa es la que manda. Las internas usan
SAVEPOINT, así que un repositorio puede envolver su propia cascada y seguir
componiendo dentro de una transacción más grande del controlador, sin que una
decida por la otra.

No hay `commit()` ni `rollback()` sueltos a propósito: llamarlos a media
`transaccion()` descuadraría su control de anidamiento. `transaccion()` es la
única puerta.
"""

import sqlite3
from contextlib import contextmanager


class BaseDeDatosNoConectada(RuntimeError):
    """Se intentó usar la base de datos antes de llamar a `connect()`."""


class Database:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self._connection = None
        self._profundidad = 0

    def connect(self):
        """Establece la conexión a la base de datos."""
        if self._connection is None:
            # isolation_level=None: el driver no abre transacciones por su
            # cuenta. Las abre transaccion() con un BEGIN explícito.
            self._connection = sqlite3.connect(self.db_file, isolation_level=None)
            self._connection.row_factory = sqlite3.Row

            # SQLite NO valida llaves foráneas por defecto, y el ajuste es por
            # conexión: no basta con el PRAGMA que trae ddl.sql, porque ese solo
            # corre la vez que se crea la base. Sin esta línea, conectarse a una
            # base ya existente deja pasar filas huérfanas en silencio.
            self._connection.execute("PRAGMA foreign_keys = ON")

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._profundidad = 0

    @property
    def conectada(self) -> bool:
        return self._connection is not None

    @property
    def en_transaccion(self) -> bool:
        """True si hay una `transaccion()` abierta ahora mismo."""
        return self._profundidad > 0

    def _exigir_conexion(self) -> sqlite3.Connection:
        if self._connection is None:
            raise BaseDeDatosNoConectada("La base de datos no está conectada.")
        return self._connection

    def execute(self, query: str, params: tuple = ()):
        """Ejecuta una consulta SQL y devuelve el cursor.

        No commitea: fuera de una `transaccion()` el driver guarda cada
        sentencia por su cuenta; dentro, manda la transacción.
        """
        conexion = self._exigir_conexion()
        cursor = conexion.cursor()
        cursor.execute(query, params)
        return cursor

    @contextmanager
    def transaccion(self):
        """Agrupa varias escrituras en una sola operación atómica.

        Anidable: la transacción externa abre el BEGIN y es la que confirma o
        deshace todo. Las internas abren un SAVEPOINT, así que si una falla y
        alguien atrapa el error más arriba, se deshace solo su parte y la
        transacción externa sigue en pie y coherente.
        """
        conexion = self._exigir_conexion()
        nivel = self._profundidad
        punto = None if nivel == 0 else f"sp_{nivel}"

        conexion.execute("BEGIN" if punto is None else f"SAVEPOINT {punto}")
        self._profundidad += 1
        try:
            yield self
        except BaseException:
            if punto is None:
                conexion.execute("ROLLBACK")
            else:
                conexion.execute(f"ROLLBACK TO {punto}")
                conexion.execute(f"RELEASE {punto}")
            raise
        else:
            conexion.execute("COMMIT" if punto is None else f"RELEASE {punto}")
        finally:
            self._profundidad -= 1
