from model.especialidad import Especialidad
from .repositorio import Repositorio

COLUMNAS = ("id_esp", "nombre", "descripcion")
CLAVE = ("id_esp",)


class EspecialidadSQLRepository(Repositorio):
    """Repositorio de especialidades."""

    @staticmethod
    def _a_entidad(row) -> Especialidad:
        """Convierte un renglon de la tabla en una Especialidad."""
        return Especialidad(**dict(row))

    @staticmethod
    def _a_fila(especialidad: Especialidad) -> dict:
        """Convierte una Especialidad en columna -> valor listo para SQLite."""
        return {
            "id_esp": especialidad.id_esp,
            "nombre": especialidad.nombre,
            "descripcion": especialidad.descripcion,
        }

    def obtener_por_id(self, id_esp: int) -> Especialidad | None:
        """Obtiene una especialidad por su ID (id_esp)."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Especialidad WHERE id_esp = ?"
        row = self.db.execute(sql, (id_esp,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las especialidades, ordenadas por nombre."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Especialidad ORDER BY nombre"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, especialidad: Especialidad) -> Especialidad:
        """Inserta una nueva especialidad y actualiza su id_esp."""
        especialidad._validar_propiedades()
        sql = "INSERT INTO Especialidad (nombre, descripcion) VALUES (?, ?)"
        cursor = self.db.execute(sql, (especialidad.nombre, especialidad.descripcion))
        especialidad.id_esp = cursor.lastrowid
        return especialidad

    def guardar(self, especialidad: Especialidad) -> bool:
        """Inserta la especialidad o actualiza la existente (upsert por id_esp)."""
        especialidad._validar_propiedades()
        cursor = self._upsert("Especialidad", self._a_fila(especialidad), CLAVE)
        if especialidad.id_esp is None:
            especialidad.id_esp = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, especialidad: Especialidad) -> bool:
        """Elimina la especialidad recibida."""
        if especialidad.id_esp is None:
            return False
        sql = "DELETE FROM Especialidad WHERE id_esp = ?"
        cursor = self.db.execute(sql, (especialidad.id_esp,))
        return cursor.rowcount > 0
