from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from model.database import Database


class Repositorio(ABC):
    """Clase base abstracta de todos los repositorios.

    Define el constructor comun al que se le inyecta la base de datos, de modo
    que las implementaciones concretas no tengan que repetirlo, y declara el
    contrato minimo que todas deben cumplir (obtener_por_id, obtener_todos,
    registrar, guardar, darbaja).

    Las consultas de lectura puntuales (obtener_por_id) reciben la llave
    primaria de su propia tabla, simple o compuesta. Las operaciones de
    escritura (registrar, guardar, darbaja) reciben la entidad del repositorio.

    Tambien ofrece dos ayudas protegidas que las implementaciones concretas
    reutilizan para no repetir el mismo armado de SQL veinte veces:
    `_filas` para los SELECT que devuelven varios renglones y `_upsert` para
    el INSERT ... ON CONFLICT ... DO UPDATE que usa `guardar`.
    """

    def __init__(self, db: Database):
        self._db = db

    @property
    def db(self) -> Database:
        """Base de datos inyectada en el repositorio."""
        return self._db

    # ------------------------------------------------------------------
    # Ayudas protegidas
    # ------------------------------------------------------------------

    def _filas(self, sql: str, params: Sequence[Any] = ()) -> list[Any]:
        """Ejecuta un SELECT y devuelve todos sus renglones."""
        return self.db.execute(sql, tuple(params)).fetchall()

    def _upsert(
        self, tabla: str, datos: Mapping[str, Any], clave: Sequence[str]
    ) -> Any:
        """INSERT ... ON CONFLICT (clave) DO UPDATE: inserta o actualiza.

        SQLite soporta UPSERT nativo desde la version 3.24, asi que `guardar`
        no necesita preguntar si el registro es nuevo o existente: lo resuelve
        la base de datos en un solo viaje.

        `datos` es columna -> valor ya convertido a tipos de SQLite. Las
        columnas de `clave` cuyo valor sea None se omiten del INSERT, para que
        SQLite asigne sola la llave AUTOINCREMENT.

        El conflicto se detecta unicamente sobre `clave`: si la fila choca con
        otro indice UNIQUE de la tabla (por ejemplo curp o numero_empleado) la
        operacion falla con IntegrityError en lugar de actualizar, que es el
        comportamiento deseado porque esa fila es otra entidad.
        """
        clave = tuple(clave)
        columnas = [
            col for col, valor in datos.items() if not (col in clave and valor is None)
        ]
        if not columnas:
            raise ValueError(f"No hay columnas que guardar en {tabla}.")

        marcadores = ", ".join("?" for _ in columnas)
        asignaciones = ", ".join(
            f"{col} = excluded.{col}" for col in columnas if col not in clave
        )
        accion = f"DO UPDATE SET {asignaciones}" if asignaciones else "DO NOTHING"
        sql = (
            f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores}) "
            f"ON CONFLICT ({', '.join(clave)}) {accion}"
        )
        return self.db.execute(sql, tuple(datos[col] for col in columnas))

    # ------------------------------------------------------------------
    # Contrato
    # ------------------------------------------------------------------

    @abstractmethod
    def obtener_por_id(self, *args: Any, **kwargs: Any) -> Any:
        """Obtiene una entidad por su llave primaria, o None si no existe."""
        raise NotImplementedError

    @abstractmethod
    def registrar(self, entidad: Any) -> Any:
        """Persiste una entidad nueva y la devuelve con su id asignado."""
        raise NotImplementedError

    @abstractmethod
    def darbaja(self, entidad: Any) -> bool:
        """Da de baja (logica o fisica) la entidad recibida.

        Recibe la entidad propia del repositorio, no su llave primaria: es el
        objeto el que sabe cual es su clave, incluso cuando es compuesta. Si la
        entidad no trae clave (nunca se persistio) devuelve False.
        """
        raise NotImplementedError

    @abstractmethod
    def guardar(self, entidad: Any) -> bool:
        """Inserta la entidad recibida o actualiza la que ya existe (upsert).

        Recibe el objeto de la entidad y hace upsert de el: si su llave
        primaria viene vacia se inserta y se le asigna la que genero SQLite;
        si ya trae llave, se actualizan las columnas con los valores del
        objeto. Devuelve True si la base de datos quedo modificada.
        """
        raise NotImplementedError

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las entidades de la tabla."""
        raise NotImplementedError
