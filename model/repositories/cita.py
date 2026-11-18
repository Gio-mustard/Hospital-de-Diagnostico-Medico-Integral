from enum import Enum

from model.cita import Cita
from model.constants import EstadosCita
from .repositorio import Repositorio

COLUMNAS = (
    "id_cita",
    "id_paciente",
    "id_medico",
    "id_recepcionista",
    "num_consultorio",
    "fecha_hora",
    "motivo",
    "estado",
    "diagnostico",
)
CLAVE = ("id_cita",)


class CitaSQLRepository(Repositorio):
    """Repositorio de citas."""

    @staticmethod
    def _a_entidad(row) -> Cita:
        """Convierte un renglon de la tabla en una Cita."""
        return Cita(**dict(row))

    @staticmethod
    def _a_fila(cita: Cita) -> dict:
        """Convierte una Cita en columna -> valor listo para SQLite."""
        return {
            "id_cita": cita.id_cita,
            "id_paciente": cita.id_paciente,
            "id_medico": cita.id_medico,
            "id_recepcionista": cita.id_recepcionista,
            "num_consultorio": cita.num_consultorio,
            "fecha_hora": (
                cita.fecha_hora.isoformat(sep=" ")
                if hasattr(cita.fecha_hora, "isoformat")
                else str(cita.fecha_hora)
            ),
            "motivo": cita.motivo,
            "estado": cita.estado.value if isinstance(cita.estado, Enum) else cita.estado,
            "diagnostico": cita.diagnostico,
        }

    def obtener_por_id(self, id_cita: int) -> Cita | None:
        """Obtiene una cita por su ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Cita WHERE id_cita = ?"
        row = self.db.execute(sql, (id_cita,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las citas, de la mas reciente a la mas antigua."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Cita ORDER BY fecha_hora DESC, id_cita DESC"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Cita) -> Cita:
        """Registra una nueva cita en la base de datos."""
        cita = entidad
        cita._validar_propiedades()
        fila = self._a_fila(cita)

        sql = """
            INSERT INTO Cita (
                id_paciente, id_medico, id_recepcionista,
                num_consultorio, fecha_hora, motivo, estado, diagnostico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql,
            (
                fila["id_paciente"],
                fila["id_medico"],
                fila["id_recepcionista"],
                fila["num_consultorio"],
                fila["fecha_hora"],
                fila["motivo"],
                fila["estado"],
                fila["diagnostico"],
            ),
        )
        cita.id_cita = cursor.lastrowid
        return cita

    def guardar(self, cita: Cita) -> bool:
        """Inserta la cita o actualiza la existente (upsert por id_cita)."""
        cita._validar_propiedades()
        cursor = self._upsert("Cita", self._a_fila(cita), CLAVE)
        if cita.id_cita is None:
            cita.id_cita = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, cita: Cita) -> bool:
        """Cancela (baja logica) la cita recibida."""
        if cita.id_cita is None:
            return False
        sql = "UPDATE Cita SET estado = ? WHERE id_cita = ?"
        cursor = self.db.execute(sql, (EstadosCita.CANCELADA.value, cita.id_cita))
        if cursor.rowcount > 0:
            cita.estado = EstadosCita.CANCELADA
            return True
        return False
