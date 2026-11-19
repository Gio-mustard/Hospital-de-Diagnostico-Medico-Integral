from abc import abstractmethod
from enum import Enum

from model.habitacion import Habitacion
from .repositorio import Repositorio

COLUMNAS = ("num_habitacion", "piso", "tipo", "estado")
CLAVE = ("num_habitacion",)


class HabitacionRepositorio(Repositorio):
    """Contrato del repositorio de habitaciones.

    Fija sobre una Habitacion las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, num_habitacion: int) -> Habitacion | None:
        """Obtiene una habitacion por su numero, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las habitaciones."""
        ...

    @abstractmethod
    def registrar(self, entidad: Habitacion) -> Habitacion:
        """Persiste una habitacion nueva y la devuelve."""
        ...

    @abstractmethod
    def guardar(self, entidad: Habitacion) -> bool:
        """Inserta la habitacion recibida o actualiza la que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Habitacion) -> bool:
        """Da de baja la habitacion recibida."""
        ...


class HabitacionSQLRepository(HabitacionRepositorio):
    """Repositorio de habitaciones."""

    @staticmethod
    def _a_entidad(row) -> Habitacion:
        """Convierte un renglon de la tabla en una Habitacion."""
        return Habitacion(**dict(row))

    @staticmethod
    def _a_fila(habitacion: Habitacion) -> dict:
        """Convierte una Habitacion en columna -> valor listo para SQLite."""
        return {
            "num_habitacion": habitacion.num_habitacion,
            "piso": habitacion.piso,
            "tipo": (
                habitacion.tipo.value
                if isinstance(habitacion.tipo, Enum)
                else habitacion.tipo
            ),
            "estado": (
                habitacion.estado.value
                if isinstance(habitacion.estado, Enum)
                else habitacion.estado
            ),
        }

    def obtener_por_id(self, num_habitacion: int) -> Habitacion | None:
        """Obtiene una habitacion por su numero (PK)."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM Habitacion
            WHERE num_habitacion = ?
        """
        row = self.db.execute(sql, (num_habitacion,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las habitaciones, ordenadas por numero."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Habitacion ORDER BY num_habitacion"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Habitacion) -> Habitacion:
        """Registra una habitacion con su PK manual num_habitacion."""
        habitacion = entidad
        habitacion._validar_propiedades()
        fila = self._a_fila(habitacion)
        sql = """
            INSERT INTO Habitacion (num_habitacion, piso, tipo, estado)
            VALUES (?, ?, ?, ?)
        """
        self.db.execute(
            sql,
            (fila["num_habitacion"], fila["piso"], fila["tipo"], fila["estado"]),
        )
        return habitacion

    def guardar(self, entidad: Habitacion) -> bool:
        """Inserta la habitacion o actualiza la existente (upsert por numero)."""
        habitacion = entidad
        habitacion._validar_propiedades()
        cursor = self._upsert("Habitacion", self._a_fila(habitacion), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, entidad: Habitacion) -> bool:
        """Elimina la habitacion recibida."""
        habitacion = entidad
        if habitacion.num_habitacion is None:
            return False
        sql = "DELETE FROM Habitacion WHERE num_habitacion = ?"
        cursor = self.db.execute(sql, (habitacion.num_habitacion,))
        return cursor.rowcount > 0
