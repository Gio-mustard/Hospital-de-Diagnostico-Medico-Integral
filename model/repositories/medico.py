from abc import abstractmethod

from model.medico import Medico
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS as COLUMNAS_DH
from .trabajador import TrabajadorSQLRepository

COLUMNAS = ("id_medico", "id_trabajador", "cedula_profesional", "activo")
COLUMNAS_LECTURA = COLUMNAS[:-1]
COLUMNAS_TRABAJADOR = ("numero_empleado", "departamento", "fecha_ingreso")
CLAVE = ("id_medico",)

SELECT_UNIDO = ", ".join(
    [f"m.{col}" for col in COLUMNAS_LECTURA]
    + [f"t.{col}" for col in COLUMNAS_TRABAJADOR]
    + [f"dh.{col}" for col in COLUMNAS_DH]
)
DESDE_UNIDO = """
    FROM Medico m
    INNER JOIN Trabajador t ON m.id_trabajador = t.id_trabajador
    INNER JOIN DerechoHabiente dh ON t.id_derechohabiente = dh.id_derechohabiente
"""


class MedicoRepositorio(Repositorio):
    """Contrato del repositorio de medicos.

    Fija sobre un Medico las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_medico: int) -> Medico | None:
        """Obtiene un medico por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los medicos."""
        ...

    @abstractmethod
    def registrar(self, entidad: Medico) -> Medico:
        """Persiste un medico nuevo y lo devuelve con su id_medico asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: Medico) -> bool:
        """Inserta el medico recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Medico) -> bool:
        """Da de baja el medico recibido."""
        ...


class MedicoSQLRepository(MedicoRepositorio):
    """Repositorio de medicos."""

    @property
    def _trab_repo(self) -> TrabajadorSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return TrabajadorSQLRepository(self.db)

    @staticmethod
    def _a_entidad(row) -> Medico:
        """Convierte un renglon del JOIN en un Medico."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Medico(**datos)

    @staticmethod
    def _a_fila(medico: Medico) -> dict:
        """Convierte un Medico en columna -> valor de su propia tabla."""
        return {
            "id_medico": medico.id_medico,
            "id_trabajador": medico.id_trabajador,
            "cedula_profesional": medico.cedula_profesional,
            "activo": int(bool(medico.activo)),
        }

    def obtener_por_id(self, id_medico: int) -> Medico | None:
        """Obtiene un medico por su ID haciendo JOIN con Trabajador y DerechoHabiente."""
        sql = f"SELECT {SELECT_UNIDO} {DESDE_UNIDO} WHERE m.id_medico = ?"
        row = self.db.execute(sql, (id_medico,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los medicos, ordenados por nombre."""
        sql = f"""
            SELECT {SELECT_UNIDO} {DESDE_UNIDO}
            ORDER BY dh.apellido_paterno, dh.apellido_materno, dh.nombres
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Medico) -> Medico:
        """Registra al medico asegurando su registro en Trabajador y DerechoHabiente."""
        with self.db.transaccion():
            medico = entidad
            medico._validar_propiedades()
            if medico.id_trabajador is None:
                self._trab_repo.registrar(medico)

            sql = "INSERT INTO Medico (id_trabajador, cedula_profesional) VALUES (?, ?)"
            cursor = self.db.execute(sql, (medico.id_trabajador, medico.cedula_profesional))
            medico.id_medico = cursor.lastrowid
            return medico

    def guardar(self, entidad: Medico) -> bool:
        """Guarda al medico completo: primero Trabajador y DerechoHabiente, luego su tabla."""
        with self.db.transaccion():
            medico = entidad
            medico._validar_propiedades()
            self._trab_repo.guardar(medico)
            cursor = self._upsert("Medico", self._a_fila(medico), CLAVE)
            if medico.id_medico is None:
                medico.id_medico = cursor.lastrowid
            return cursor.rowcount > 0

    def darbaja(self, entidad: Medico) -> bool:
        """Da de baja logica al medico recibido, via su DerechoHabiente."""
        with self.db.transaccion():
            medico = entidad
            if medico.id_derechohabiente is None or medico.id_trabajador is None:
                if medico.id_medico is None:
                    return False
                sql_find = """
                    SELECT m.id_trabajador, t.id_derechohabiente
                    FROM Medico m
                    INNER JOIN Trabajador t ON m.id_trabajador = t.id_trabajador
                    WHERE m.id_medico = ?
                """
                row = self.db.execute(sql_find, (medico.id_medico,)).fetchone()
                if not row:
                    return False
                medico.id_trabajador = row["id_trabajador"]
                medico.id_derechohabiente = row["id_derechohabiente"]

            if not self._trab_repo.darbaja(medico):
                return False
            self.db.execute(
                "UPDATE Medico SET activo = 0 WHERE id_trabajador = ?",
                (medico.id_trabajador,),
            )
            return True
