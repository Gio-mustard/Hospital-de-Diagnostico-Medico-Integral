from abc import abstractmethod
from enum import Enum

from model.consultorio import Consultorio
from .repositorio import Repositorio

COLUMNAS = ("num_consultorio", "piso", "departamento", "estado")
CLAVE = ("num_consultorio",)


class ConsultorioRepositorio(Repositorio):
    """Contrato del repositorio de consultorios.

    Fija sobre un Consultorio las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, num_consultorio: int) -> Consultorio | None:
        """Obtiene un consultorio por su numero, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los consultorios."""
        ...

    @abstractmethod
    def registrar(self, entidad: Consultorio) -> Consultorio:
        """Persiste un consultorio nuevo y lo devuelve."""
        ...

    @abstractmethod
    def guardar(self, entidad: Consultorio) -> bool:
        """Inserta el consultorio recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Consultorio) -> bool:
        """Da de baja el consultorio recibido."""
        ...


class ConsultorioSQLRepository(ConsultorioRepositorio):
    """Repositorio de consultorios."""

    @staticmethod
    def _a_entidad(row) -> Consultorio:
        """Convierte un renglon de la tabla en un Consultorio."""
        return Consultorio(**dict(row))

    @staticmethod
    def _a_fila(consultorio: Consultorio) -> dict:
        """Convierte un Consultorio en columna -> valor listo para SQLite."""
        return {
            "num_consultorio": consultorio.num_consultorio,
            "piso": consultorio.piso,
            "departamento": consultorio.departamento,
            "estado": (
                consultorio.estado.value
                if isinstance(consultorio.estado, Enum)
                else consultorio.estado
            ),
        }

    def obtener_por_id(self, num_consultorio: int) -> Consultorio | None:
        """Obtiene un consultorio por su numero (PK)."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM Consultorio
            WHERE num_consultorio = ?
        """
        row = self.db.execute(sql, (num_consultorio,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los consultorios, ordenados por numero."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Consultorio ORDER BY num_consultorio"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Consultorio) -> Consultorio:
        """Registra un consultorio con su PK manual num_consultorio."""
        consultorio = entidad
        consultorio._validar_propiedades()
        fila = self._a_fila(consultorio)
        sql = """
            INSERT INTO Consultorio (num_consultorio, piso, departamento, estado)
            VALUES (?, ?, ?, ?)
        """
        self.db.execute(
            sql,
            (
                fila["num_consultorio"],
                fila["piso"],
                fila["departamento"],
                fila["estado"],
            ),
        )
        return consultorio

    def guardar(self, entidad: Consultorio) -> bool:
        """Inserta el consultorio o actualiza el existente (upsert por numero)."""
        consultorio = entidad
        consultorio._validar_propiedades()
        cursor = self._upsert("Consultorio", self._a_fila(consultorio), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, entidad: Consultorio) -> bool:
        """Elimina el consultorio recibido."""
        consultorio = entidad
        if consultorio.num_consultorio is None:
            return False
        sql = "DELETE FROM Consultorio WHERE num_consultorio = ?"
        cursor = self.db.execute(sql, (consultorio.num_consultorio,))
        return cursor.rowcount > 0
