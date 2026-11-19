from abc import abstractmethod
from enum import Enum

from model.recepcionista import Recepcionista
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS_SIN_CLAVE as COLUMNAS_DH
from .derechohabiente import DerechoHabienteSQLRepository

COLUMNAS = (
    "id_recepcionista",
    "id_derechohabiente",
    "id_trabajador",
    "turno",
    "modulo_atencion",
    "extension_tel",
    "activo",
)
COLUMNAS_LECTURA = COLUMNAS[:-1]
CLAVE = ("id_recepcionista",)

SELECT_UNIDO = ", ".join(
    [f"r.{col}" for col in COLUMNAS_LECTURA] + [f"dh.{col}" for col in COLUMNAS_DH]
)
DESDE_UNIDO = """
    FROM Recepcionista r
    INNER JOIN DerechoHabiente dh ON r.id_derechohabiente = dh.id_derechohabiente
"""


class RecepcionistaRepositorio(Repositorio):
    """Contrato del repositorio de recepcionistas.

    Fija sobre una Recepcionista las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_recepcionista: int) -> Recepcionista | None:
        """Obtiene una recepcionista por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las recepcionistas."""
        ...

    @abstractmethod
    def registrar(self, entidad: Recepcionista) -> Recepcionista:
        """Persiste una recepcionista nueva y la devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Recepcionista) -> bool:
        """Inserta la recepcionista recibida o actualiza la que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Recepcionista) -> bool:
        """Da de baja la recepcionista recibida."""
        ...


class RecepcionistaSQLRepository(RecepcionistaRepositorio):
    """Repositorio de recepcionistas."""

    @property
    def _dh_repo(self) -> DerechoHabienteSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return DerechoHabienteSQLRepository(self.db)

    @staticmethod
    def _a_entidad(row) -> Recepcionista:
        """Convierte un renglon del JOIN en una Recepcionista."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Recepcionista(**datos)

    @staticmethod
    def _a_fila(recep: Recepcionista) -> dict:
        """Convierte una Recepcionista en columna -> valor de su propia tabla."""
        return {
            "id_recepcionista": recep.id_recepcionista,
            "id_derechohabiente": recep.id_derechohabiente,
            "id_trabajador": recep.id_trabajador,
            "turno": recep.turno.value if isinstance(recep.turno, Enum) else recep.turno,
            "modulo_atencion": recep.modulo_atencion,
            "extension_tel": recep.extension_tel,
            "activo": int(bool(recep.activo)),
        }

    def obtener_por_id(self, id_recepcionista: int) -> Recepcionista | None:
        """Obtiene una recepcionista por su ID haciendo JOIN con DerechoHabiente."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} WHERE r.id_recepcionista = ?"
        row = self.db.execute(sql, (id_recepcionista,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las recepcionistas, ordenadas por turno y nombre."""
        sql = f"""
            SELECT {SELECT_UNIDO} {DESDE_UNIDO}
            ORDER BY r.turno, dh.apellido_paterno, dh.apellido_materno, dh.nombres
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Recepcionista) -> Recepcionista:
        """Registra una recepcionista (y su DerechoHabiente si aun no existe)."""
        with self.db.transaccion():
            recep = entidad
            recep._validar_propiedades()
            if recep.id_derechohabiente is None:
                self._dh_repo.registrar(recep)

            fila = self._a_fila(recep)
            sql = """
                INSERT INTO Recepcionista (
                    id_derechohabiente, id_trabajador, turno, modulo_atencion, extension_tel
                ) VALUES (?, ?, ?, ?, ?)
            """
            cursor = self.db.execute(
                sql,
                (
                    fila["id_derechohabiente"],
                    fila["id_trabajador"],
                    fila["turno"],
                    fila["modulo_atencion"],
                    fila["extension_tel"],
                ),
            )
            recep.id_recepcionista = cursor.lastrowid
            return recep

    def guardar(self, entidad: Recepcionista) -> bool:
        """Guarda a la recepcionista completa: primero su DerechoHabiente, luego su tabla."""
        with self.db.transaccion():
            recep = entidad
            recep._validar_propiedades()
            self._dh_repo.guardar(recep)
            cursor = self._upsert("Recepcionista", self._a_fila(recep), CLAVE)
            if recep.id_recepcionista is None:
                recep.id_recepcionista = cursor.lastrowid
            return cursor.rowcount > 0

    def darbaja(self, entidad: Recepcionista) -> bool:
        """Da de baja logica a la recepcionista recibida, via su DerechoHabiente."""
        with self.db.transaccion():
            recep = entidad
            if recep.id_derechohabiente is None:
                if recep.id_recepcionista is None:
                    return False
                row = self.db.execute(
                    "SELECT id_derechohabiente FROM Recepcionista WHERE id_recepcionista = ?",
                    (recep.id_recepcionista,),
                ).fetchone()
                if not row:
                    return False
                recep.id_derechohabiente = row["id_derechohabiente"]

            if not self._dh_repo.darbaja(recep):
                return False
            self.db.execute(
                "UPDATE Recepcionista SET activo = 0 WHERE id_derechohabiente = ?",
                (recep.id_derechohabiente,),
            )
            return True
