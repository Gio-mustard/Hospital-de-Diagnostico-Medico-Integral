"""Cimiento comun de las pruebas de repositorios.

`RepositorioTestCase` monta una base de datos nueva en memoria por cada prueba
y le aplica `ddl.sql`. Usar el DDL real y no un esquema recortado es a
proposito: asi las pruebas tambien cubren los CHECK, los UNIQUE, las llaves
foraneas y los triggers, que son parte del contrato que los repositorios
asumen.

Las fabricas (`crear_paciente`, `crear_medico`, ...) no arman las filas con
INSERT a mano: usan los repositorios de cada entidad. De ese modo los datos de
prueba se construyen por el mismo camino que la app, y una fabrica que se rompe
es en si misma una senal de que algo se rompio.

Las entidades que casi todas las pruebas necesitan de fondo (un paciente, un
medico, una habitacion...) estan como propiedades perezosas: se crean la
primera vez que se piden y se reutilizan dentro de la misma prueba, para no
llenar la base de filas que nadie mira.

`ContratoRepositorioMixin` junta las pruebas que TODO repositorio debe pasar
(que la interfaz sea abstracta, que la implementacion la cumpla, que los
metodos de escritura reciban `entidad`). Cada modulo las hereda fijando su
par interfaz/implementacion, en vez de repetirlas veinte veces.
"""

import inspect
import unittest
from datetime import date, timedelta
from pathlib import Path

from model.cita import Cita
from model.consultorio import Consultorio
from model.database import Database
from model.derechohabiente import DerechoHabiente
from model.enfermero import Enfermero
from model.especialidad import Especialidad
from model.habitacion import Habitacion
from model.ingreso_emergencia import IngresoEmergencia
from model.medicamento import Medicamento
from model.medico import Medico
from model.paciente import Paciente
from model.recepcionista import Recepcionista
from model.receta import Receta
from model.trabajador import Trabajador
from model.usuario import Usuario
from model.repositories import (
    CitaSQLRepository,
    ConsultorioSQLRepository,
    DerechoHabienteSQLRepository,
    EnfermeroSQLRepository,
    EspecialidadSQLRepository,
    HabitacionSQLRepository,
    IngresoEmergenciaSQLRepository,
    MedicamentoSQLRepository,
    MedicoSQLRepository,
    PacienteSQLRepository,
    RecepcionistaSQLRepository,
    RecetaSQLRepository,
    Repositorio,
    TrabajadorSQLRepository,
    UsuarioSQLRepository,
)

RAIZ = Path(__file__).resolve().parent.parent
DDL = (RAIZ / "ddl.sql").read_text(encoding="utf-8")

METODOS_DEL_CONTRATO = (
    "obtener_por_id",
    "obtener_todos",
    "registrar",
    "guardar",
    "darbaja",
)
METODOS_DE_ESCRITURA = ("registrar", "guardar", "darbaja")

TRATAMIENTO = {
    "diagnostico": "Gastritis leve",
    "medicamentos": ["Omeprazol 20mg"],
    "indicaciones_generales": "Ayuno de 8 horas",
}


class RepositorioTestCase(unittest.TestCase):
    """Base de datos limpia en memoria, una por prueba."""

    def setUp(self) -> None:
        self.db = Database(":memory:")
        self.db.connect()

        # `Database` no expone executescript (solo corre una sentencia por
        # llamada), y el DDL son ~40 sentencias: hay que bajar a la conexion.
        self.db._connection.executescript(DDL)

        # SQLite no valida llaves foraneas por defecto, y el PRAGMA del DDL no
        # sobrevive al executescript. Se vuelve a poner aqui porque varias
        # pruebas dependen de que las FK se respeten.
        self.db.execute("PRAGMA foreign_keys = ON")

        self._consecutivo = 0
        self._cache: dict[str, object] = {}

    def tearDown(self) -> None:
        self.db.close()

    # ------------------------------------------------------------------
    # Datos irrepetibles
    # ------------------------------------------------------------------

    def _siguiente(self) -> int:
        """Contador por prueba, para no chocar con los UNIQUE del DDL."""
        self._consecutivo += 1
        return self._consecutivo

    def _curp(self, n: int, sexo: str = "M") -> str:
        """CURP de relleno que cumple el GLOB de 18 posiciones del DDL."""
        return f"TST{chr(ord('A') + n % 26)}900101{sexo}BCNNN{n % 10}{n // 10 % 10}"

    def _telefono(self, n: int) -> str:
        """Telefono E.164 de relleno."""
        return f"+5268600{n:05d}"

    def _datos_persona(self, n: int, sexo: str = "M") -> dict:
        """Columnas que toda entidad hereda de DerechoHabiente."""
        return {
            "nombres": f"Nombre{n}",
            "apellido_paterno": f"Paterno{n}",
            "apellido_materno": f"Materno{n}",
            "direccion_calle": f"Calle {n}",
            "codigo_postal": "21100",
            "ciudad": "Mexicali",
            "estado": "Baja California",
            "fecha_nacimiento": "1990-01-01",
            "genero": "Femenino" if sexo == "M" else "Masculino",
            "telefono": self._telefono(n),
            "curp": self._curp(n, sexo),
        }

    def _datos_trabajador(self, n: int) -> dict:
        """Columnas que toda entidad hereda de Trabajador."""
        return {
            "numero_empleado": f"EMP-{n:04d}",
            "departamento": "Medicina Interna",
            "fecha_ingreso": "2015-03-01",
        }

    # ------------------------------------------------------------------
    # Fabricas: devuelven la entidad ya persistida, con su id asignado
    # ------------------------------------------------------------------

    def crear_derechohabiente(self, **cambios) -> DerechoHabiente:
        n = self._siguiente()
        datos = self._datos_persona(n) | cambios
        return DerechoHabienteSQLRepository(self.db).registrar(DerechoHabiente(**datos))

    def crear_paciente(self, **cambios) -> Paciente:
        n = self._siguiente()
        datos = self._datos_persona(n) | {"tipo_sangre": "O+"} | cambios
        return PacienteSQLRepository(self.db).registrar(Paciente(**datos))

    def crear_trabajador(self, **cambios) -> Trabajador:
        n = self._siguiente()
        datos = self._datos_persona(n) | self._datos_trabajador(n) | cambios
        return TrabajadorSQLRepository(self.db).registrar(Trabajador(**datos))

    def crear_medico(self, **cambios) -> Medico:
        n = self._siguiente()
        datos = (
            self._datos_persona(n, "H")
            | self._datos_trabajador(n)
            | {"cedula_profesional": f"{1000000 + n}"}
            | cambios
        )
        return MedicoSQLRepository(self.db).registrar(Medico(**datos))

    def crear_enfermero(self, **cambios) -> Enfermero:
        n = self._siguiente()
        datos = self._datos_persona(n) | self._datos_trabajador(n) | cambios
        return EnfermeroSQLRepository(self.db).registrar(Enfermero(**datos))

    def crear_recepcionista(self, **cambios) -> Recepcionista:
        n = self._siguiente()
        datos = (
            self._datos_persona(n)
            | {"turno": "Matutino", "modulo_atencion": "Admisión Principal"}
            | cambios
        )
        return RecepcionistaSQLRepository(self.db).registrar(Recepcionista(**datos))

    def crear_consultorio(self, **cambios) -> Consultorio:
        n = self._siguiente()
        datos = {
            "num_consultorio": 100 + n,
            "piso": 1,
            "departamento": "Medicina Interna",
            "estado": "Disponible",
        } | cambios
        return ConsultorioSQLRepository(self.db).registrar(Consultorio(**datos))

    def crear_habitacion(self, **cambios) -> Habitacion:
        n = self._siguiente()
        datos = {
            "num_habitacion": 200 + n,
            "piso": 2,
            "tipo": "Individual",
            "estado": "Disponible",
        } | cambios
        return HabitacionSQLRepository(self.db).registrar(Habitacion(**datos))

    def crear_especialidad(self, **cambios) -> Especialidad:
        n = self._siguiente()
        datos = {"nombre": f"Especialidad {n}", "descripcion": "Descripción"} | cambios
        return EspecialidadSQLRepository(self.db).registrar(Especialidad(**datos))

    def crear_medicamento(self, **cambios) -> Medicamento:
        n = self._siguiente()
        # El trigger trg_medicamento_caducidad_ins exige al menos 15 dias de
        # margen; se usan 90 para que la prueba no caduque con el calendario.
        datos = {
            "nombre": f"Medicamento {n}",
            "presentacion": "Tabletas 500mg",
            "stock": 50,
            "lote": f"L-{n:04d}",
            "caducidad": date.today() + timedelta(days=90),
            "disponible": True,
        } | cambios
        return MedicamentoSQLRepository(self.db).registrar(Medicamento(**datos))

    def crear_cita(self, **cambios) -> Cita:
        datos = {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
            "fecha_hora": "2026-12-01 10:30:00",
            "motivo": "Dolor abdominal",
        } | cambios
        return CitaSQLRepository(self.db).registrar(Cita(**datos))

    def crear_ingreso_emergencia(self, **cambios) -> IngresoEmergencia:
        datos = {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
            "fecha_hora": "2026-12-01 03:15:00",
            "motivo": "Dolor torácico",
            "nivel_urgencia": "Alto",
        } | cambios
        return IngresoEmergenciaSQLRepository(self.db).registrar(
            IngresoEmergencia(**datos)
        )

    def crear_receta(self, **cambios) -> Receta:
        if "id_cita" not in cambios and "id_ingreso_emergencia" not in cambios:
            cambios = {"id_cita": self.crear_cita().id_cita} | cambios
        datos = {
            "fecha_emision": "2026-12-01",
            "tratamiento": dict(TRATAMIENTO),
        } | cambios
        return RecetaSQLRepository(self.db).registrar(Receta(**datos))

    def crear_usuario(self, **cambios) -> Usuario:
        n = self._siguiente()
        datos = {
            "id": f"{n:032d}",  # LONGITUD_UUID = 32
            "hash_contrasena": "$2b$12$" + "x" * 53,
            "correo": f"usuario{n}@hospital.com",
            "rol": "Médico",
        } | cambios
        return UsuarioSQLRepository(self.db).registrar(Usuario(**datos))

    # ------------------------------------------------------------------
    # Entidades de fondo, creadas solo si la prueba las pide
    # ------------------------------------------------------------------

    def _perezoso(self, nombre: str, fabrica):
        if nombre not in self._cache:
            self._cache[nombre] = fabrica()
        return self._cache[nombre]

    @property
    def paciente(self) -> Paciente:
        return self._perezoso("paciente", self.crear_paciente)

    @property
    def medico(self) -> Medico:
        return self._perezoso("medico", self.crear_medico)

    @property
    def enfermero(self) -> Enfermero:
        return self._perezoso("enfermero", self.crear_enfermero)

    @property
    def recepcionista(self) -> Recepcionista:
        return self._perezoso("recepcionista", self.crear_recepcionista)

    @property
    def habitacion(self) -> Habitacion:
        return self._perezoso("habitacion", self.crear_habitacion)

    @property
    def consultorio(self) -> Consultorio:
        return self._perezoso("consultorio", self.crear_consultorio)

    @property
    def especialidad(self) -> Especialidad:
        return self._perezoso("especialidad", self.crear_especialidad)

    @property
    def medicamento(self) -> Medicamento:
        return self._perezoso("medicamento", self.crear_medicamento)

    # ------------------------------------------------------------------
    # Aserciones sobre la base, sin pasar por el repositorio que se prueba
    # ------------------------------------------------------------------

    def contar(self, tabla: str) -> int:
        """Cuantas filas tiene la tabla."""
        return self.db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    def leer_fila(self, tabla: str, **filtros) -> dict | None:
        """Lee una fila cruda, para comprobar lo que de verdad quedo escrito."""
        donde = " AND ".join(f"{col} = ?" for col in filtros)
        fila = self.db.execute(
            f"SELECT * FROM {tabla} WHERE {donde}", tuple(filtros.values())
        ).fetchone()
        return dict(fila) if fila else None


class ContratoRepositorioMixin:
    """Pruebas que todo repositorio debe pasar, sea cual sea su entidad.

    Se usa junto con `RepositorioTestCase`, fijando el par de clases:

        class ContratoDeEspecialidad(ContratoRepositorioMixin, RepositorioTestCase):
            interfaz = EspecialidadRepositorio
            implementacion = EspecialidadSQLRepository
    """

    interfaz: type = None
    implementacion: type = None

    def test_la_implementacion_cumple_la_interfaz(self):
        self.assertTrue(issubclass(self.implementacion, self.interfaz))
        self.assertTrue(issubclass(self.interfaz, Repositorio))

    def test_la_interfaz_es_abstracta(self):
        with self.assertRaises(TypeError):
            self.interfaz(self.db)

    def test_la_implementacion_se_puede_instanciar(self):
        self.assertIsInstance(self.implementacion(self.db), self.interfaz)

    def test_la_interfaz_declara_el_contrato_completo(self):
        for metodo in METODOS_DEL_CONTRATO:
            with self.subTest(metodo=metodo):
                self.assertTrue(
                    getattr(self.interfaz, metodo).__isabstractmethod__,
                    f"{self.interfaz.__name__}.{metodo} deberia ser @abstractmethod",
                )
                self.assertFalse(
                    getattr(
                        getattr(self.implementacion, metodo), "__isabstractmethod__", False
                    ),
                    f"{self.implementacion.__name__}.{metodo} quedo sin implementar",
                )

    def test_los_metodos_de_escritura_reciben_entidad(self):
        """La firma heredada de Repositorio nombra al argumento `entidad`."""
        for clase in (self.interfaz, self.implementacion):
            for metodo in METODOS_DE_ESCRITURA:
                with self.subTest(clase=clase.__name__, metodo=metodo):
                    argumentos = list(
                        inspect.signature(getattr(clase, metodo)).parameters
                    )
                    self.assertEqual(argumentos[:2], ["self", "entidad"])

    def test_la_base_de_datos_inyectada_es_la_que_se_usa(self):
        repo = self.implementacion(self.db)
        self.assertIs(repo.db, self.db)
