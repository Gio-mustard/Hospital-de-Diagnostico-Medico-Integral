from enum import Enum

from model.consultorio import Consultorio
from .repositorio import Repositorio

#: Columnas de la tabla Consultorio.
COLUMNAS = ("num_consultorio", "piso", "departamento", "estado")
#: Llave primaria manual (sin AUTOINCREMENT).
CLAVE = ("num_consultorio",)


class ConsultorioSQLRepository(Repositorio):
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

    def registrar(self, consultorio: Consultorio) -> Consultorio:
        """Registra un consultorio con su PK manual num_consultorio."""
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

    def guardar(self, consultorio: Consultorio) -> bool:
        """Inserta el consultorio o actualiza el existente (upsert por numero)."""
        consultorio._validar_propiedades()
        cursor = self._upsert("Consultorio", self._a_fila(consultorio), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, consultorio: Consultorio) -> bool:
        """Elimina el consultorio recibido."""
        if consultorio.num_consultorio is None:
            return False
        sql = "DELETE FROM Consultorio WHERE num_consultorio = ?"
        cursor = self.db.execute(sql, (consultorio.num_consultorio,))
        return cursor.rowcount > 0
