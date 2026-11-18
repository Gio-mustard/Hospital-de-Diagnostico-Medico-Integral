import json

from model.receta import Receta
from .repositorio import Repositorio

COLUMNAS = (
    "id_receta",
    "id_cita",
    "id_ingreso_emergencia",
    "fecha_emision",
    "tratamiento",
)
CLAVE = ("id_receta",)


class RecetaSQLRepository(Repositorio):
    """Repositorio de recetas."""

    @staticmethod
    def _a_entidad(row) -> Receta:
        """Convierte un renglon de la tabla en una Receta, deserializando el JSON."""
        datos = dict(row)
        if isinstance(datos.get("tratamiento"), str):
            datos["tratamiento"] = json.loads(datos["tratamiento"])
        return Receta(**datos)

    @staticmethod
    def _a_fila(receta: Receta) -> dict:
        """Convierte una Receta en columna -> valor listo para SQLite."""
        return {
            "id_receta": receta.id_receta,
            "id_cita": receta.id_cita,
            "id_ingreso_emergencia": receta.id_ingreso_emergencia,
            "fecha_emision": (
                receta.fecha_emision.isoformat()
                if hasattr(receta.fecha_emision, "isoformat")
                else str(receta.fecha_emision)
            ),
            "tratamiento": (
                json.dumps(receta.tratamiento, ensure_ascii=False)
                if isinstance(receta.tratamiento, dict)
                else receta.tratamiento
            ),
        }

    def obtener_por_id(self, id_receta: int) -> Receta | None:
        """Obtiene una receta por su ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Receta WHERE id_receta = ?"
        row = self.db.execute(sql, (id_receta,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las recetas, de la mas reciente a la mas antigua."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM Receta
            ORDER BY fecha_emision DESC, id_receta DESC
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, receta: Receta) -> Receta:
        """Inserta una nueva receta medica."""
        receta._validar_propiedades()
        fila = self._a_fila(receta)

        sql = """
            INSERT INTO Receta (
                id_cita, id_ingreso_emergencia, fecha_emision, tratamiento
            ) VALUES (?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql,
            (
                fila["id_cita"],
                fila["id_ingreso_emergencia"],
                fila["fecha_emision"],
                fila["tratamiento"],
            ),
        )
        receta.id_receta = cursor.lastrowid
        return receta

    def guardar(self, receta: Receta) -> bool:
        """Inserta la receta o actualiza la existente (upsert por id_receta)."""
        receta._validar_propiedades()
        cursor = self._upsert("Receta", self._a_fila(receta), CLAVE)
        if receta.id_receta is None:
            receta.id_receta = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, receta: Receta) -> bool:
        """Elimina la receta recibida."""
        if receta.id_receta is None:
            return False
        sql = "DELETE FROM Receta WHERE id_receta = ?"
        cursor = self.db.execute(sql, (receta.id_receta,))
        return cursor.rowcount > 0
