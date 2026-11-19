from abc import abstractmethod

from model.detalle_receta import DetalleReceta
from .repositorio import Repositorio

COLUMNAS = ("id_receta", "id_medicamento", "dosis_indicaciones")
CLAVE = ("id_receta", "id_medicamento")


class DetalleRecetaRepositorio(Repositorio):
    """Contrato del repositorio de detalles de receta.

    Fija sobre un DetalleReceta las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_receta: int, id_medicamento: int) -> DetalleReceta | None:
        """Obtiene un renglon de receta por su PK compuesta, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los renglones de receta."""
        ...

    @abstractmethod
    def registrar(self, entidad: DetalleReceta) -> DetalleReceta:
        """Persiste un renglon de receta nuevo y lo devuelve."""
        ...

    @abstractmethod
    def guardar(self, entidad: DetalleReceta) -> bool:
        """Inserta el renglon de receta recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: DetalleReceta) -> bool:
        """Da de baja el renglon de receta recibido."""
        ...


class DetalleRecetaSQLRepository(DetalleRecetaRepositorio):
    """Repositorio de detalles de receta."""

    @staticmethod
    def _a_entidad(row) -> DetalleReceta:
        """Convierte un renglon de la tabla en un DetalleReceta."""
        return DetalleReceta(**dict(row))

    @staticmethod
    def _a_fila(detalle: DetalleReceta) -> dict:
        """Convierte un DetalleReceta en columna -> valor listo para SQLite."""
        return {
            "id_receta": detalle.id_receta,
            "id_medicamento": detalle.id_medicamento,
            "dosis_indicaciones": detalle.dosis_indicaciones,
        }

    def obtener_por_id(self, id_receta: int, id_medicamento: int) -> DetalleReceta | None:
        """Obtiene un renglon de receta por su PK compuesta (id_receta, id_medicamento)."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM DetalleReceta
            WHERE id_receta = ? AND id_medicamento = ?
        """
        row = self.db.execute(sql, (id_receta, id_medicamento)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los renglones de receta, agrupados por receta."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM DetalleReceta
            ORDER BY id_receta, id_medicamento
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: DetalleReceta) -> DetalleReceta:
        """Inserta un detalle de receta."""
        detalle = entidad
        detalle._validar_propiedades()
        sql = """
            INSERT INTO DetalleReceta (id_receta, id_medicamento, dosis_indicaciones)
            VALUES (?, ?, ?)
        """
        self.db.execute(
            sql,
            (detalle.id_receta, detalle.id_medicamento, detalle.dosis_indicaciones),
        )
        return detalle

    def guardar(self, entidad: DetalleReceta) -> bool:
        """Inserta el renglon de receta o actualiza el existente (upsert por PK compuesta)."""
        detalle = entidad
        detalle._validar_propiedades()
        cursor = self._upsert("DetalleReceta", self._a_fila(detalle), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, entidad: DetalleReceta) -> bool:
        """Elimina el renglon de receta recibido (PK compuesta)."""
        detalle = entidad
        if detalle.id_receta is None or detalle.id_medicamento is None:
            return False
        sql = "DELETE FROM DetalleReceta WHERE id_receta = ? AND id_medicamento = ?"
        cursor = self.db.execute(sql, (detalle.id_receta, detalle.id_medicamento))
        return cursor.rowcount > 0
