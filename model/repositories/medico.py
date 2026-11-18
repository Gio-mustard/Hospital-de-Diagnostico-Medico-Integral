from model.medico import Medico
from .repositorio import Repositorio
from .derechohabiente import COLUMNAS as COLUMNAS_DH
from .trabajador import TrabajadorSQLRepository

#: Columnas propias de la tabla Medico. `activo` se repite aqui, pero el valor
#: que se escribe siempre es el heredado del DerechoHabiente.
COLUMNAS = ("id_medico", "id_trabajador", "cedula_profesional", "activo")
#: Columnas propias que se leen: `activo` se lee del DerechoHabiente.
COLUMNAS_LECTURA = COLUMNAS[:-1]
#: Columnas heredadas de Trabajador que se leen en el JOIN.
COLUMNAS_TRABAJADOR = ("numero_empleado", "departamento", "fecha_ingreso")
#: Llave primaria AUTOINCREMENT.
CLAVE = ("id_medico",)

#: Lista de SELECT del JOIN con Trabajador y DerechoHabiente.
SELECT_UNIDO = ", ".join(
    [f"m.{col}" for col in COLUMNAS_LECTURA]
    + [f"t.{col}" for col in COLUMNAS_TRABAJADOR]
    + [f"dh.{col}" for col in COLUMNAS_DH]
)
#: FROM comun de las lecturas.
DESDE_UNIDO = """
    FROM Medico m
    INNER JOIN Trabajador t ON m.id_trabajador = t.id_trabajador
    INNER JOIN DerechoHabiente dh ON t.id_derechohabiente = dh.id_derechohabiente
"""


class MedicoSQLRepository(Repositorio):
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

    def registrar(self, medico: Medico) -> Medico:
        """Registra al medico asegurando su registro en Trabajador y DerechoHabiente."""
        medico._validar_propiedades()
        if medico.id_trabajador is None:
            self._trab_repo.registrar(medico)

        sql = "INSERT INTO Medico (id_trabajador, cedula_profesional) VALUES (?, ?)"
        cursor = self.db.execute(sql, (medico.id_trabajador, medico.cedula_profesional))
        medico.id_medico = cursor.lastrowid
        return medico

    def guardar(self, medico: Medico) -> bool:
        """Guarda al medico completo: primero Trabajador y DerechoHabiente, luego su tabla."""
        medico._validar_propiedades()
        self._trab_repo.guardar(medico)
        cursor = self._upsert("Medico", self._a_fila(medico), CLAVE)
        if medico.id_medico is None:
            medico.id_medico = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, medico: Medico) -> bool:
        """Da de baja logica al medico recibido, via su DerechoHabiente."""
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
        # La columna `activo` de Medico refleja la del DerechoHabiente.
        self.db.execute(
            "UPDATE Medico SET activo = 0 WHERE id_trabajador = ?",
            (medico.id_trabajador,),
        )
        return True
