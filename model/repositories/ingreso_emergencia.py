from enum import Enum

from model.ingreso_emergencia import IngresoEmergencia
from .repositorio import Repositorio

#: Columnas de la tabla IngresoEmergencia.
COLUMNAS = (
    "id_ingreso_emergencia",
    "id_paciente",
    "id_medico",
    "id_recepcionista",
    "num_habitacion",
    "fecha_hora",
    "motivo",
    "nivel_urgencia",
    "diagnostico",
)
#: Llave primaria AUTOINCREMENT.
CLAVE = ("id_ingreso_emergencia",)


class IngresoEmergenciaSQLRepository(Repositorio):
    """Repositorio de ingresos de emergencia."""

    @staticmethod
    def _a_entidad(row) -> IngresoEmergencia:
        """Convierte un renglon de la tabla en un IngresoEmergencia."""
        return IngresoEmergencia(**dict(row))

    @staticmethod
    def _a_fila(emergencia: IngresoEmergencia) -> dict:
        """Convierte un IngresoEmergencia en columna -> valor listo para SQLite."""
        return {
            "id_ingreso_emergencia": emergencia.id_ingreso_emergencia,
            "id_paciente": emergencia.id_paciente,
            "id_medico": emergencia.id_medico,
            "id_recepcionista": emergencia.id_recepcionista,
            "num_habitacion": emergencia.num_habitacion,
            "fecha_hora": (
                emergencia.fecha_hora.isoformat(sep=" ")
                if hasattr(emergencia.fecha_hora, "isoformat")
                else str(emergencia.fecha_hora)
            ),
            "motivo": emergencia.motivo,
            "nivel_urgencia": (
                emergencia.nivel_urgencia.value
                if isinstance(emergencia.nivel_urgencia, Enum)
                else emergencia.nivel_urgencia
            ),
            "diagnostico": emergencia.diagnostico,
        }

    def obtener_por_id(self, id_ingreso_emergencia: int) -> IngresoEmergencia | None:
        """Obtiene un ingreso de emergencia por su ID."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM IngresoEmergencia
            WHERE id_ingreso_emergencia = ?
        """
        row = self.db.execute(sql, (id_ingreso_emergencia,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los ingresos de emergencia, del mas reciente al mas antiguo."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM IngresoEmergencia
            ORDER BY fecha_hora DESC, id_ingreso_emergencia DESC
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, emergencia: IngresoEmergencia) -> IngresoEmergencia:
        """Registra un nuevo ingreso de emergencia."""
        emergencia._validar_propiedades()
        fila = self._a_fila(emergencia)

        sql = """
            INSERT INTO IngresoEmergencia (
                id_paciente, id_medico, id_recepcionista, num_habitacion,
                fecha_hora, motivo, nivel_urgencia, diagnostico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql,
            (
                fila["id_paciente"],
                fila["id_medico"],
                fila["id_recepcionista"],
                fila["num_habitacion"],
                fila["fecha_hora"],
                fila["motivo"],
                fila["nivel_urgencia"],
                fila["diagnostico"],
            ),
        )
        emergencia.id_ingreso_emergencia = cursor.lastrowid
        return emergencia

    def guardar(self, emergencia: IngresoEmergencia) -> bool:
        """Inserta el ingreso de emergencia o actualiza el existente (upsert)."""
        emergencia._validar_propiedades()
        cursor = self._upsert("IngresoEmergencia", self._a_fila(emergencia), CLAVE)
        if emergencia.id_ingreso_emergencia is None:
            emergencia.id_ingreso_emergencia = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, emergencia: IngresoEmergencia) -> bool:
        """Elimina el ingreso de emergencia recibido."""
        if emergencia.id_ingreso_emergencia is None:
            return False
        sql = "DELETE FROM IngresoEmergencia WHERE id_ingreso_emergencia = ?"
        cursor = self.db.execute(sql, (emergencia.id_ingreso_emergencia,))
        return cursor.rowcount > 0
