from abc import abstractmethod

from model.enfermero import Enfermero
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS as COLUMNAS_DH
from .trabajador import TrabajadorSQLRepository

COLUMNAS = ("id_enfermero", "id_trabajador", "activo")
COLUMNAS_LECTURA = COLUMNAS[:-1]
COLUMNAS_TRABAJADOR = ("numero_empleado", "departamento", "fecha_ingreso")
CLAVE = ("id_enfermero",)

SELECT_UNIDO = ", ".join(
    [f"e.{col}" for col in COLUMNAS_LECTURA]
    + [f"t.{col}" for col in COLUMNAS_TRABAJADOR]
    + [f"dh.{col}" for col in COLUMNAS_DH]
)
DESDE_UNIDO = """
    FROM Enfermero e
    INNER JOIN Trabajador t ON e.id_trabajador = t.id_trabajador
    INNER JOIN DerechoHabiente dh ON t.id_derechohabiente = dh.id_derechohabiente
"""


class EnfermeroRepositorio(Repositorio):
    """Contrato del repositorio de enfermeros.

    Fija sobre un Enfermero las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_enfermero: int) -> Enfermero | None:
        """Obtiene un enfermero por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los enfermeros."""
        ...

    @abstractmethod
    def registrar(self, entidad: Enfermero) -> Enfermero:
        """Persiste un enfermero nuevo y lo devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Enfermero) -> bool:
        """Inserta el enfermero recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Enfermero) -> bool:
        """Da de baja el enfermero recibido."""
        ...


class EnfermeroSQLRepository(EnfermeroRepositorio):
    """Repositorio de enfermeros."""

    @property
    def _trab_repo(self) -> TrabajadorSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return TrabajadorSQLRepository(self.db)

    @staticmethod
    def _a_entidad(row) -> Enfermero:
        """Convierte un renglon del JOIN en un Enfermero."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Enfermero(**datos)

    @staticmethod
    def _a_fila(enfermero: Enfermero) -> dict:
        """Convierte un Enfermero en columna -> valor de su propia tabla."""
        return {
            "id_enfermero": enfermero.id_enfermero,
            "id_trabajador": enfermero.id_trabajador,
            "activo": int(bool(enfermero.activo)),
        }

    def obtener_por_id(self, id_enfermero: int) -> Enfermero | None:
        """Obtiene un enfermero por su ID haciendo JOIN con Trabajador y DerechoHabiente."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} WHERE e.id_enfermero = ?"
        row = self.db.execute(sql, (id_enfermero,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los enfermeros, ordenados por nombre."""
        sql = f"""
            SELECT {SELECT_UNIDO} {DESDE_UNIDO}
            ORDER BY dh.apellido_paterno, dh.apellido_materno, dh.nombres
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Enfermero) -> Enfermero:
        """Registra al enfermero asegurando su registro previo en Trabajador y DerechoHabiente."""
        with self.db.transaccion():
            enfermero = entidad
            enfermero._validar_propiedades()
            if enfermero.id_trabajador is None:
                self._trab_repo.registrar(enfermero)

            sql = "INSERT INTO Enfermero (id_trabajador) VALUES (?)"
            cursor = self.db.execute(sql, (enfermero.id_trabajador,))
            enfermero.id_enfermero = cursor.lastrowid
            return enfermero

    def guardar(self, entidad: Enfermero) -> bool:
        """Guarda al enfermero completo: primero Trabajador y DerechoHabiente, luego su tabla."""
        with self.db.transaccion():
            enfermero = entidad
            enfermero._validar_propiedades()
            self._trab_repo.guardar(enfermero)
            cursor = self._upsert("Enfermero", self._a_fila(enfermero), CLAVE)
            if enfermero.id_enfermero is None:
                enfermero.id_enfermero = cursor.lastrowid
            return cursor.rowcount > 0

    def darbaja(self, entidad: Enfermero) -> bool:
        """Da de baja logica al enfermero recibido, via su DerechoHabiente."""
        with self.db.transaccion():
            enfermero = entidad
            if enfermero.id_derechohabiente is None or enfermero.id_trabajador is None:
                if enfermero.id_enfermero is None:
                    return False
                sql_find = """
                    SELECT e.id_trabajador, t.id_derechohabiente
                    FROM Enfermero e
                    INNER JOIN Trabajador t ON e.id_trabajador = t.id_trabajador
                    WHERE e.id_enfermero = ?
                """
                row = self.db.execute(sql_find, (enfermero.id_enfermero,)).fetchone()
                if not row:
                    return False
                enfermero.id_trabajador = row["id_trabajador"]
                enfermero.id_derechohabiente = row["id_derechohabiente"]

            if not self._trab_repo.darbaja(enfermero):
                return False
            self.db.execute(
                "UPDATE Enfermero SET activo = 0 WHERE id_trabajador = ?",
                (enfermero.id_trabajador,),
            )
            return True
