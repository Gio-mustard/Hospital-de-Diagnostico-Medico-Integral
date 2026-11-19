from abc import abstractmethod

from model.medicamento import Medicamento
from .repositorio import Repositorio

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
CLAVE = ("id_medicamento",)


class MedicamentoRepositorio(Repositorio):
    """Contrato del repositorio de medicamentos.

    Fija sobre un Medicamento las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_medicamento: int) -> Medicamento | None:
        """Obtiene un medicamento por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los medicamentos."""
        ...

    @abstractmethod
    def registrar(self, entidad: Medicamento) -> Medicamento:
        """Persiste un medicamento nuevo y lo devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Medicamento) -> bool:
        """Inserta el medicamento recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Medicamento) -> bool:
        """Da de baja el medicamento recibido."""
        ...


class MedicamentoSQLRepository(MedicamentoRepositorio):
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

    def registrar(self, entidad: Medicamento) -> Medicamento:
        """Registra un nuevo medicamento en inventario."""
        med = entidad
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

    def guardar(self, entidad: Medicamento) -> bool:
        """Inserta el medicamento o actualiza el existente (upsert por id)."""
        med = entidad
        med._validar_propiedades()
        cursor = self._upsert("Medicamento", self._a_fila(med), CLAVE)
        if med.id_medicamento is None:
            med.id_medicamento = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, entidad: Medicamento) -> bool:
        """Da de baja logica el medicamento recibido (stock = 0, disponible = 0)."""
        med = entidad
        if med.id_medicamento is None:
            return False
        sql = "UPDATE Medicamento SET stock = 0, disponible = 0 WHERE id_medicamento = ?"
        cursor = self.db.execute(sql, (med.id_medicamento,))
        if cursor.rowcount > 0:
            med.stock = 0
            med.disponible = False
            return True
        return False
