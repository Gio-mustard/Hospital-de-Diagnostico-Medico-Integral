from abc import abstractmethod
from enum import Enum

from model.paciente import Paciente
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS_SIN_CLAVE as COLUMNAS_DH
from .derechohabiente import DerechoHabienteSQLRepository

COLUMNAS = ("id_paciente", "id_derechohabiente", "tipo_sangre")
CLAVE = ("id_paciente",)

SELECT_UNIDO = ", ".join(
    [f"p.{col}" for col in COLUMNAS] + [f"dh.{col}" for col in COLUMNAS_DH]
)
DESDE_UNIDO = """
    FROM Paciente p
    INNER JOIN DerechoHabiente dh ON p.id_derechohabiente = dh.id_derechohabiente
"""


class PacienteRepositorio(Repositorio):
    """Contrato del repositorio de pacientes.

    Fija sobre un Paciente las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_paciente: int) -> Paciente | None:
        """Obtiene un paciente por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los pacientes."""
        ...

    @abstractmethod
    def registrar(self, entidad: Paciente) -> Paciente:
        """Persiste un paciente nuevo y lo devuelve con su id_paciente asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Paciente) -> bool:
        """Inserta el paciente recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Paciente) -> bool:
        """Da de baja el paciente recibido."""
        ...


class PacienteSQLRepository(PacienteRepositorio):
    """Repositorio de pacientes."""

    @property
    def _dh_repo(self) -> DerechoHabienteSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return DerechoHabienteSQLRepository(self.db)

    @staticmethod
    def _a_entidad(row) -> Paciente:
        """Convierte un renglon del JOIN en un Paciente."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Paciente(**datos)

    @staticmethod
    def _a_fila(paciente: Paciente) -> dict:
        """Convierte un Paciente en columna -> valor de su propia tabla."""
        return {
            "id_paciente": paciente.id_paciente,
            "id_derechohabiente": paciente.id_derechohabiente,
            "tipo_sangre": (
                paciente.tipo_sangre.value
                if isinstance(paciente.tipo_sangre, Enum)
                else paciente.tipo_sangre
            ),
        }

    def obtener_por_id(self, id_paciente: int) -> Paciente | None:
        """Obtiene un paciente por su ID haciendo JOIN con DerechoHabiente."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} WHERE p.id_paciente = ?"
        row = self.db.execute(sql, (id_paciente,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los pacientes, ordenados por nombre."""
        sql = f"""
            SELECT {SELECT_UNIDO} {DESDE_UNIDO}
            ORDER BY dh.apellido_paterno, dh.apellido_materno, dh.nombres
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Paciente) -> Paciente:
        """Registra un paciente (y su DerechoHabiente si aun no tiene id_derechohabiente)."""
        with self.db.transaccion():
            paciente = entidad
            paciente._validar_propiedades()
            if paciente.id_derechohabiente is None:
                self._dh_repo.registrar(paciente)

            fila = self._a_fila(paciente)
            sql = "INSERT INTO Paciente (id_derechohabiente, tipo_sangre) VALUES (?, ?)"
            cursor = self.db.execute(
                sql, (fila["id_derechohabiente"], fila["tipo_sangre"])
            )
            paciente.id_paciente = cursor.lastrowid
            return paciente

    def guardar(self, entidad: Paciente) -> bool:
        """Guarda al paciente completo: primero su DerechoHabiente, luego su propia tabla."""
        with self.db.transaccion():
            paciente = entidad
            paciente._validar_propiedades()
            self._dh_repo.guardar(paciente)
            cursor = self._upsert("Paciente", self._a_fila(paciente), CLAVE)
            if paciente.id_paciente is None:
                paciente.id_paciente = cursor.lastrowid
            return cursor.rowcount > 0

    def darbaja(self, entidad: Paciente) -> bool:
        """Da de baja logica al paciente recibido, via su DerechoHabiente."""
        with self.db.transaccion():
            paciente = entidad
            if paciente.id_derechohabiente is None:
                if paciente.id_paciente is None:
                    return False
                row = self.db.execute(
                    "SELECT id_derechohabiente FROM Paciente WHERE id_paciente = ?",
                    (paciente.id_paciente,),
                ).fetchone()
                if not row:
                    return False
                paciente.id_derechohabiente = row["id_derechohabiente"]
            return self._dh_repo.darbaja(paciente)
