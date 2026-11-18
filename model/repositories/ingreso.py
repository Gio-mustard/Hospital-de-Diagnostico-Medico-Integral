from datetime import datetime

from model.ingreso import Ingreso
from .repositorio import Repositorio

COLUMNAS = (
    "id_ingreso",
    "fecha_ingreso",
    "fecha_alta",
    "id_cita",
    "num_habitacion",
    "id_recepcionista",
)
CLAVE = ("id_ingreso",)


class IngresoSQLRepository(Repositorio):
    """Repositorio de ingresos hospitalarios."""

    @staticmethod
    def _a_entidad(row) -> Ingreso:
        """Convierte un renglon de la tabla en un Ingreso."""
        return Ingreso(**dict(row))

    @staticmethod
    def _a_fila(ingreso: Ingreso) -> dict:
        """Convierte un Ingreso en columna -> valor listo para SQLite."""
        return {
            "id_ingreso": ingreso.id_ingreso,
            "fecha_ingreso": (
                ingreso.fecha_ingreso.isoformat(sep=" ")
                if hasattr(ingreso.fecha_ingreso, "isoformat")
                else str(ingreso.fecha_ingreso)
            ),
            "fecha_alta": (
                ingreso.fecha_alta.isoformat(sep=" ")
                if hasattr(ingreso.fecha_alta, "isoformat")
                else ingreso.fecha_alta
            ),
            "id_cita": ingreso.id_cita,
            "num_habitacion": ingreso.num_habitacion,
            "id_recepcionista": ingreso.id_recepcionista,
        }

    def obtener_por_id(self, id_ingreso: int) -> Ingreso | None:
        """Obtiene un ingreso por su ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Ingreso WHERE id_ingreso = ?"
        row = self.db.execute(sql, (id_ingreso,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los ingresos, del mas reciente al mas antiguo."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM Ingreso
            ORDER BY fecha_ingreso DESC, id_ingreso DESC
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, ingreso: Ingreso) -> Ingreso:
        """Registra un nuevo ingreso hospitalario."""
        ingreso._validar_propiedades()
        fila = self._a_fila(ingreso)

        sql = """
            INSERT INTO Ingreso (
                fecha_ingreso, fecha_alta, id_cita, num_habitacion, id_recepcionista
            ) VALUES (?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql,
            (
                fila["fecha_ingreso"],
                fila["fecha_alta"],
                fila["id_cita"],
                fila["num_habitacion"],
                fila["id_recepcionista"],
            ),
        )
        ingreso.id_ingreso = cursor.lastrowid
        return ingreso

    def guardar(self, ingreso: Ingreso) -> bool:
        """Inserta el ingreso o actualiza el existente (upsert por id_ingreso)."""
        ingreso._validar_propiedades()
        cursor = self._upsert("Ingreso", self._a_fila(ingreso), CLAVE)
        if ingreso.id_ingreso is None:
            ingreso.id_ingreso = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, ingreso: Ingreso) -> bool:
        """Da de alta el internamiento recibido asignandole fecha_alta.

        Si la entidad ya trae `fecha_alta` se respeta ese valor; si no, se usa
        el momento actual y se refleja de vuelta en la entidad.
        """
        if ingreso.id_ingreso is None:
            return False
        alta = ingreso.fecha_alta if ingreso.fecha_alta is not None else datetime.now()
        alta_str = alta.isoformat(sep=" ") if hasattr(alta, "isoformat") else str(alta)
        sql = "UPDATE Ingreso SET fecha_alta = ? WHERE id_ingreso = ?"
        cursor = self.db.execute(sql, (alta_str, ingreso.id_ingreso))
        if cursor.rowcount > 0:
            ingreso.fecha_alta = alta
            return True
        return False
