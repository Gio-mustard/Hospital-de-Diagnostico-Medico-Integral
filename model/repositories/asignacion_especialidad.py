from model.asignacion_especialidad import (
    AsignacionEspecialidad,
    MedicoEspecialidad,
    EnfermeroEspecialidad,
)
from .repositorio import Repositorio

COLUMNAS_COMUNES = ("id_esp", "documentos", "institucion")
MEDICO = ("MedicoEspecialidad", "id_medico", MedicoEspecialidad)
ENFERMERO = ("EnfermeroEspecialidad", "id_enfermero", EnfermeroEspecialidad)


def _columnas(col_titular: str) -> tuple[str, ...]:
    """Columnas de una de las dos tablas, el titular primero."""
    return (col_titular,) + COLUMNAS_COMUNES


class AsignacionEspecialidadSQLRepository(Repositorio):
    """Repositorio para MedicoEspecialidad y EnfermeroEspecialidad."""

    @staticmethod
    def _destino(entidad: AsignacionEspecialidad) -> tuple:
        """Devuelve (tabla, columna_titular, clase) segun el tipo de la entidad."""
        if isinstance(entidad, EnfermeroEspecialidad):
            return ENFERMERO
        if isinstance(entidad, MedicoEspecialidad):
            return MEDICO
        raise TypeError("Se esperaba MedicoEspecialidad o EnfermeroEspecialidad.")

    @staticmethod
    def _a_fila(entidad: AsignacionEspecialidad, col_titular: str) -> dict:
        """Convierte una asignacion en columna -> valor listo para SQLite."""
        return {
            col_titular: entidad.id_titular,
            "id_esp": entidad.id_esp,
            "documentos": entidad.documentos,
            "institucion": entidad.institucion,
        }

    def _obtener_de(self, destino: tuple) -> tuple:
        """Lee todos los renglones de una de las dos tablas."""
        tabla, col_titular, clase = destino
        columnas = _columnas(col_titular)
        sql = f"""
            SELECT {', '.join(columnas)}
            FROM {tabla}
            ORDER BY {col_titular}, id_esp
        """
        return tuple(clase(**dict(row)) for row in self._filas(sql))

    def obtener_por_id(
        self, id_titular: int, id_esp: int, es_enfermero: bool = False
    ) -> MedicoEspecialidad | EnfermeroEspecialidad | None:
        """Obtiene una asignacion por su PK compuesta (id_titular, id_esp)."""
        tabla, col_titular, clase = ENFERMERO if es_enfermero else MEDICO
        columnas = _columnas(col_titular)
        sql = f"""
            SELECT {', '.join(columnas)}
            FROM {tabla}
            WHERE {col_titular} = ? AND id_esp = ?
        """
        row = self.db.execute(sql, (id_titular, id_esp)).fetchone()
        return clase(**dict(row)) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las asignaciones: primero medicos, luego enfermeros."""
        return self._obtener_de(MEDICO) + self._obtener_de(ENFERMERO)

    def registrar(self, entidad: AsignacionEspecialidad) -> AsignacionEspecialidad:
        """Registra una asignacion de especialidad (Medico o Enfermero)."""
        entidad._validar_propiedades()
        tabla, col_titular, _ = self._destino(entidad)
        columnas = _columnas(col_titular)
        fila = self._a_fila(entidad, col_titular)

        sql = f"""
            INSERT INTO {tabla} ({', '.join(columnas)})
            VALUES ({', '.join('?' for _ in columnas)})
        """
        self.db.execute(sql, tuple(fila[col] for col in columnas))
        return entidad

    def guardar(self, entidad: AsignacionEspecialidad) -> bool:
        """Inserta la asignacion o actualiza la existente (upsert por PK compuesta)."""
        entidad._validar_propiedades()
        tabla, col_titular, _ = self._destino(entidad)
        cursor = self._upsert(
            tabla, self._a_fila(entidad, col_titular), (col_titular, "id_esp")
        )
        return cursor.rowcount > 0

    def darbaja(self, entidad: AsignacionEspecialidad) -> bool:
        """Elimina la asignacion de especialidad recibida (PK compuesta)."""
        tabla, col_titular, _ = self._destino(entidad)
        if entidad.id_titular is None or entidad.id_esp is None:
            return False
        sql = f"DELETE FROM {tabla} WHERE {col_titular} = ? AND id_esp = ?"
        cursor = self.db.execute(sql, (entidad.id_titular, entidad.id_esp))
        return cursor.rowcount > 0
