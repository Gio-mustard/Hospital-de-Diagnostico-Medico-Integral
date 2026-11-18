from model.medicamento import Medicamento
from .repositorio import Repositorio

#: Columnas de la tabla Medicamento.
COLUMNAS = (
    "id_medicamento",
    "nombre",
    "presentacion",
    "stock",
    "lote",
    "caducidad",
    "disponible",
    "proximo_pedido",
)
#: Llave primaria AUTOINCREMENT.
CLAVE = ("id_medicamento",)


class MedicamentoSQLRepository(Repositorio):
    """Repositorio de medicamentos."""

    @staticmethod
    def _a_entidad(row) -> Medicamento:
        """Convierte un renglon de la tabla en un Medicamento."""
        datos = dict(row)
        datos["disponible"] = bool(datos["disponible"])
        return Medicamento(**datos)

    @staticmethod
    def _a_fila(med: Medicamento) -> dict:
        """Convierte un Medicamento en columna -> valor listo para SQLite."""
        return {
            "id_medicamento": med.id_medicamento,
            "nombre": med.nombre,
            "presentacion": med.presentacion,
            "stock": med.stock,
            "lote": med.lote,
            "caducidad": (
                med.caducidad.isoformat()
                if hasattr(med.caducidad, "isoformat")
                else str(med.caducidad)
            ),
            "disponible": int(bool(med.disponible)),
            "proximo_pedido": (
                med.proximo_pedido.isoformat()
                if hasattr(med.proximo_pedido, "isoformat")
                else med.proximo_pedido
            ),
        }

    def obtener_por_id(self, id_medicamento: int) -> Medicamento | None:
        """Obtiene un medicamento por su ID."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM Medicamento
            WHERE id_medicamento = ?
        """
        row = self.db.execute(sql, (id_medicamento,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los medicamentos, ordenados por nombre."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Medicamento ORDER BY nombre, lote"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, med: Medicamento) -> Medicamento:
        """Registra un nuevo medicamento en inventario."""
        med._validar_propiedades()
        fila = self._a_fila(med)

        sql = """
            INSERT INTO Medicamento (
                nombre, presentacion, stock, lote,
                caducidad, disponible, proximo_pedido
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql,
            (
                fila["nombre"],
                fila["presentacion"],
                fila["stock"],
                fila["lote"],
                fila["caducidad"],
                fila["disponible"],
                fila["proximo_pedido"],
            ),
        )
        med.id_medicamento = cursor.lastrowid
        return med

    def guardar(self, med: Medicamento) -> bool:
        """Inserta el medicamento o actualiza el existente (upsert por id)."""
        med._validar_propiedades()
        cursor = self._upsert("Medicamento", self._a_fila(med), CLAVE)
        if med.id_medicamento is None:
            med.id_medicamento = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, med: Medicamento) -> bool:
        """Da de baja logica el medicamento recibido (stock = 0, disponible = 0)."""
        if med.id_medicamento is None:
            return False
        sql = "UPDATE Medicamento SET stock = 0, disponible = 0 WHERE id_medicamento = ?"
        cursor = self.db.execute(sql, (med.id_medicamento,))
        if cursor.rowcount > 0:
            med.stock = 0
            med.disponible = False
            return True
        return False
