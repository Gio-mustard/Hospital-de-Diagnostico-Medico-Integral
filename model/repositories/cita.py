from abc import abstractmethod
from enum import Enum
from datetime import date
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


class CitaRepositorio(Repositorio):
    """Contrato del repositorio de citas.

    Fija sobre una Cita las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_cita: int) -> Cita | None:
        """Obtiene una cita por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las citas."""
        ...

    @abstractmethod
    def registrar(self, entidad: Cita) -> Cita:
        """Persiste una cita nueva y la devuelve con su id_cita asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Cita) -> bool:
        """Inserta la cita recibida o actualiza la que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Cita) -> bool:
        """Da de baja (cancela) la cita recibida.

        Es baja logica: la fila se queda y solo pasa a estado 'Cancelada'.

        Una cita ya Completada no se puede cancelar y levanta ValueError. Si la
        cita no trae llave o ya no existe en la base, devuelve False.
        """
        ...


class CitaSQLRepository(CitaRepositorio):
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
                if hasattr(cita.fecha_hora, "isoformat") and isinstance(cita.fecha_hora,date)
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

    def guardar(self, entidad: Cita) -> bool:
        """Inserta la cita o actualiza la existente (upsert por id_cita)."""
        cita = entidad
        cita._validar_propiedades()
        cursor = self._upsert("Cita", self._a_fila(cita), CLAVE)
        if cita.id_cita is None:
            cita.id_cita = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, entidad: Cita) -> bool:
        """Cancela (baja logica) la cita recibida.

        Una cita ya Completada no se puede cancelar: la atencion ocurrio y su
        diagnostico es parte del expediente. Cancelarla ademas violaria
        `chk_cita_diagnostico_coherente` del DDL, que exige diagnostico NULL
        cuando el estado no es 'Completada'.

        El estado que decide es el de la base, no el de la entidad recibida,
        porque esta puede venir desactualizada. Devuelve False si la cita no
        trae llave o ya no existe, y levanta ValueError si esta Completada.
        """
        with self.db.transaccion():
            cita = entidad
            if cita.id_cita is None:
                return False

            fila = self.db.execute(
                "SELECT estado FROM Cita WHERE id_cita = ?", (cita.id_cita,)
            ).fetchone()
            if fila is None:
                return False
            if fila["estado"] == EstadosCita.COMPLETADA.value:
                raise ValueError(
                    f"La cita {cita.id_cita} ya esta Completada y no se puede cancelar."
                )

            # El `AND estado <> 'Completada'` no es redundante: cierra la ventana
            # entre el SELECT de arriba y este UPDATE, de modo que el CHECK del DDL
            # nunca se pueda alcanzar.
            sql = "UPDATE Cita SET estado = ? WHERE id_cita = ? AND estado <> ?"
            cursor = self.db.execute(
                sql,
                (
                    EstadosCita.CANCELADA.value,
                    cita.id_cita,
                    EstadosCita.COMPLETADA.value,
                ),
            )
            if cursor.rowcount > 0:
                cita.estado = EstadosCita.CANCELADA
                return True
            return False
