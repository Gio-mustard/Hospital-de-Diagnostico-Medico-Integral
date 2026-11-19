from abc import abstractmethod

from model.trabajador import Trabajador
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS_SIN_CLAVE as COLUMNAS_DH
from .derechohabiente import DerechoHabienteSQLRepository

COLUMNAS = (
    "id_trabajador",
    "id_derechohabiente",
    "numero_empleado",
    "departamento",
    "fecha_ingreso",
    "activo",
)
COLUMNAS_LECTURA = COLUMNAS[:-1]
CLAVE = ("id_trabajador",)

SELECT_UNIDO = ", ".join(
    [f"t.{col}" for col in COLUMNAS_LECTURA] + [f"dh.{col}" for col in COLUMNAS_DH]
)
DESDE_UNIDO = """
    FROM Trabajador t
    INNER JOIN DerechoHabiente dh ON t.id_derechohabiente = dh.id_derechohabiente
"""


class TrabajadorRepositorio(Repositorio):
    """Contrato del repositorio de trabajadores.

    Fija sobre un Trabajador las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_trabajador: int) -> Trabajador | None:
        """Obtiene un trabajador por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los trabajadores."""
        ...

    @abstractmethod
    def registrar(self, entidad: Trabajador) -> Trabajador:
        """Persiste un trabajador nuevo y lo devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Trabajador) -> bool:
        """Inserta el trabajador recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Trabajador) -> bool:
        """Da de baja el trabajador recibido."""
        ...


class TrabajadorSQLRepository(TrabajadorRepositorio):
    """Repositorio de trabajadores."""

    @property
    def _dh_repo(self) -> DerechoHabienteSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return DerechoHabienteSQLRepository(self.db)

    @staticmethod
    def _a_entidad(row) -> Trabajador:
        """Convierte un renglon del JOIN en un Trabajador."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Trabajador(**datos)

    @staticmethod
    def _a_fila(trabajador: Trabajador) -> dict:
        """Convierte un Trabajador en columna -> valor de su propia tabla."""
        return {
            "id_trabajador": trabajador.id_trabajador,
            "id_derechohabiente": trabajador.id_derechohabiente,
            "numero_empleado": trabajador.numero_empleado,
            "departamento": trabajador.departamento,
            "fecha_ingreso": (
                trabajador.fecha_ingreso.isoformat()
                if hasattr(trabajador.fecha_ingreso, "isoformat")
                else str(trabajador.fecha_ingreso)
            ),
            "activo": int(bool(trabajador.activo)),
        }

    def obtener_por_id(self, id_trabajador: int) -> Trabajador | None:
        """Obtiene un trabajador por su ID haciendo JOIN con DerechoHabiente."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} WHERE t.id_trabajador = ?"
        row = self.db.execute(sql, (id_trabajador,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los trabajadores, ordenados por numero de empleado."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} ORDER BY t.numero_empleado"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Trabajador) -> Trabajador:
        """Registra un trabajador (y su DerechoHabiente si aun no existe)."""
        with self.db.transaccion():
            trabajador = entidad
            trabajador._validar_propiedades()
            if trabajador.id_derechohabiente is None:
                self._dh_repo.registrar(trabajador)

            fila = self._a_fila(trabajador)
            sql = """
                INSERT INTO Trabajador (
                    id_derechohabiente, numero_empleado, departamento, fecha_ingreso
                ) VALUES (?, ?, ?, ?)
            """
            cursor = self.db.execute(
                sql,
                (
                    fila["id_derechohabiente"],
                    fila["numero_empleado"],
                    fila["departamento"],
                    fila["fecha_ingreso"],
                ),
            )
            trabajador.id_trabajador = cursor.lastrowid
            return trabajador

    def guardar(self, entidad: Trabajador) -> bool:
        """Guarda al trabajador completo: primero su DerechoHabiente, luego su propia tabla."""
        with self.db.transaccion():
            trabajador = entidad
            trabajador._validar_propiedades()
            self._dh_repo.guardar(trabajador)
            cursor = self._upsert("Trabajador", self._a_fila(trabajador), CLAVE)
            if trabajador.id_trabajador is None:
                trabajador.id_trabajador = cursor.lastrowid
            return cursor.rowcount > 0

    def darbaja(self, entidad: Trabajador) -> bool:
        """Da de baja logica al trabajador recibido, via su DerechoHabiente."""
        with self.db.transaccion():
            trabajador = entidad
            if trabajador.id_derechohabiente is None:
                if trabajador.id_trabajador is None:
                    return False
                row = self.db.execute(
                    "SELECT id_derechohabiente FROM Trabajador WHERE id_trabajador = ?",
                    (trabajador.id_trabajador,),
                ).fetchone()
                if not row:
                    return False
                trabajador.id_derechohabiente = row["id_derechohabiente"]

            if not self._dh_repo.darbaja(trabajador):
                return False
            self.db.execute(
                "UPDATE Trabajador SET activo = 0 WHERE id_derechohabiente = ?",
                (trabajador.id_derechohabiente,),
            )
            return True
