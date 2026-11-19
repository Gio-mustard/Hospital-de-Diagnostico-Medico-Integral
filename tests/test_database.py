"""Pruebas de Database: llaves foraneas y transacciones.

Estas dos cosas no se pueden probar con `RepositorioTestCase`, porque ese ya
levanta la base con todo puesto. Aqui se arma la conexion a mano, y varias
pruebas usan un archivo en disco en vez de `:memory:`, porque el punto es
justamente lo que pasa al CONECTARSE a una base que ya existe.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from model.database import BaseDeDatosNoConectada, Database

from .base import DDL


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = str(Path(self.carpeta.name) / "hospital.db")
        self.abiertas: list[Database] = []

    def tearDown(self) -> None:
        for db in self.abiertas:
            db.close()
        self.carpeta.cleanup()

    def abrir(self, ruta: str | None = None) -> Database:
        db = Database(ruta or self.ruta)
        db.connect()
        self.abiertas.append(db)
        return db

    def crear_base(self) -> None:
        """Aplica el DDL una vez y cierra, como el montaje inicial del sistema."""
        db = Database(self.ruta)
        db.connect()
        db._connection.executescript(DDL)
        db.close()


class ConexionYLlavesForaneas(DatabaseTestCase):
    """SQLite no valida FK por defecto, y el ajuste es por conexion."""

    def test_connect_enciende_las_llaves_foraneas(self):
        db = self.abrir(":memory:")

        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_las_llaves_siguen_encendidas_en_una_base_ya_existente(self):
        """El PRAGMA de ddl.sql solo corre al crear la base; este es el caso real."""
        self.crear_base()

        db = self.abrir()

        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_una_fila_huerfana_se_rechaza_al_reconectar(self):
        self.crear_base()
        db = self.abrir()

        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(
                """INSERT INTO Cita (id_paciente, id_medico, fecha_hora, motivo, estado)
                   VALUES (9999, 8888, '2026-12-01 10:00:00', 'X', 'Programada')"""
            )

        self.assertEqual(db.execute("SELECT COUNT(*) FROM Cita").fetchone()[0], 0)

    def test_reconectar_vuelve_a_encender_el_pragma(self):
        db = self.abrir(":memory:")
        db.close()
        db.connect()

        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_usar_la_base_sin_conectar_avisa_claro(self):
        db = Database(":memory:")

        with self.assertRaises(BaseDeDatosNoConectada):
            db.execute("SELECT 1")

    def test_conectada_dice_la_verdad(self):
        db = Database(":memory:")
        self.assertFalse(db.conectada)
        db.connect()
        self.assertTrue(db.conectada)
        db.close()
        self.assertFalse(db.conectada)


class IndicesDelEsquema(DatabaseTestCase):
    """El lado hijo de cada FK tiene que estar indexado.

    SQLite indexa solo la PK y los UNIQUE. Sin indice en la columna que
    REFERENCIA, hacer valer un ON DELETE RESTRICT obliga a recorrer la tabla
    hija completa. Esta prueba existe para que un cambio futuro al DDL no
    reintroduzca el descuido sin que nadie se entere.
    """

    def setUp(self) -> None:
        super().setUp()
        self.db = self.abrir(":memory:")
        self.db._connection.executescript(DDL)

    def _tablas(self) -> list[str]:
        return [
            r[0]
            for r in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]

    def _primeras_columnas_indexadas(self, tabla: str) -> set[str]:
        """Un indice sobre (a, b) sirve para buscar por `a`."""
        primeras = set()
        for idx in self.db.execute(f"PRAGMA index_list({tabla})"):
            columnas = [
                r["name"] for r in self.db.execute(f"PRAGMA index_info({idx['name']})")
            ]
            if columnas:
                primeras.add(columnas[0])
        return primeras

    def _alias_de_rowid(self, tabla: str) -> str | None:
        """Una PK de una sola columna INTEGER ES el rowid: no necesita indice."""
        pks = [r for r in self.db.execute(f"PRAGMA table_info({tabla})") if r["pk"] > 0]
        if len(pks) == 1 and pks[0]["type"].upper() == "INTEGER":
            return pks[0]["name"]
        return None

    def test_ninguna_fk_se_queda_sin_indice(self):
        sin_indice = []
        for tabla in self._tablas():
            indexadas = self._primeras_columnas_indexadas(tabla)
            rowid = self._alias_de_rowid(tabla)
            for fk in self.db.execute(f"PRAGMA foreign_key_list({tabla})"):
                columna = fk["from"]
                if columna != rowid and columna not in indexadas:
                    sin_indice.append(f"{tabla}.{columna} -> {fk['table']}")

        self.assertEqual(
            sin_indice,
            [],
            "estas FK recorren la tabla hija completa al validar el RESTRICT",
        )

    def test_borrar_un_padre_no_recorre_tablas_completas(self):
        """Los cuatro DELETE que el codigo de verdad ejecuta, mas el CASCADE."""
        borrados = {
            "Especialidad": "DELETE FROM Especialidad WHERE id_esp = 1",
            "Habitacion": "DELETE FROM Habitacion WHERE num_habitacion = 1",
            "Consultorio": "DELETE FROM Consultorio WHERE num_consultorio = 1",
            "IngresoEmergencia": (
                "DELETE FROM IngresoEmergencia WHERE id_ingreso_emergencia = 1"
            ),
            "Receta": "DELETE FROM Receta WHERE id_receta = 1",
        }
        for tabla, sql in borrados.items():
            with self.subTest(tabla=tabla):
                plan = [
                    r[3]
                    for r in self.db.execute(f"EXPLAIN QUERY PLAN {sql}")
                    if "SCAN" in r[3]
                ]
                self.assertEqual(plan, [], f"borrar en {tabla} recorre tablas enteras")


class Transacciones(DatabaseTestCase):
    """`execute` ya no commitea: el agrupamiento lo decide quien llama."""

    def setUp(self) -> None:
        super().setUp()
        self.db = self.abrir(":memory:")
        self.db.execute("CREATE TABLE t (n INTEGER)")

    def contar(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM t").fetchone()[0]

    def test_una_sentencia_suelta_se_guarda_sola(self):
        """Sin transaccion abierta no hay que acordarse de commitear."""
        self.db.execute("INSERT INTO t VALUES (1)")

        self.assertEqual(self.contar(), 1)
        self.assertFalse(self.db.en_transaccion)

    def test_una_transaccion_que_termina_bien_confirma_todo(self):
        with self.db.transaccion():
            self.db.execute("INSERT INTO t VALUES (1)")
            self.db.execute("INSERT INTO t VALUES (2)")

        self.assertEqual(self.contar(), 2)

    def test_una_transaccion_que_revienta_no_deja_nada(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaccion():
                self.db.execute("INSERT INTO t VALUES (1)")
                self.db.execute("INSERT INTO t VALUES (2)")
                raise RuntimeError("algo salió mal a la mitad")

        self.assertEqual(self.contar(), 0, "debio deshacer las dos inserciones")

    def test_en_transaccion_dice_si_hay_una_abierta(self):
        self.assertFalse(self.db.en_transaccion)
        with self.db.transaccion():
            self.assertTrue(self.db.en_transaccion)
        self.assertFalse(self.db.en_transaccion)

    def test_el_contador_de_anidamiento_vuelve_a_cero_tras_un_error(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaccion():
                raise RuntimeError("boom")

        self.assertFalse(self.db.en_transaccion)
        self.db.execute("INSERT INTO t VALUES (1)")  # la base sigue usable
        self.assertEqual(self.contar(), 1)


class TransaccionesAnidadas(DatabaseTestCase):
    """La externa manda; las internas son SAVEPOINT para poder deshacerse solas."""

    def setUp(self) -> None:
        super().setUp()
        self.db = self.abrir(":memory:")
        self.db.execute("CREATE TABLE t (n INTEGER)")

    def contar(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM t").fetchone()[0]

    def test_la_externa_es_la_que_confirma(self):
        with self.db.transaccion():
            with self.db.transaccion():
                self.db.execute("INSERT INTO t VALUES (1)")
            # la interna ya salio, pero nada se confirma hasta cerrar la externa
            self.assertTrue(self.db.en_transaccion)

        self.assertEqual(self.contar(), 1)

    def test_un_error_adentro_deshace_todo_si_nadie_lo_atrapa(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaccion():
                self.db.execute("INSERT INTO t VALUES (1)")
                with self.db.transaccion():
                    self.db.execute("INSERT INTO t VALUES (2)")
                    raise RuntimeError("boom")

        self.assertEqual(self.contar(), 0)

    def test_si_alguien_atrapa_el_error_solo_se_deshace_la_parte_interna(self):
        """Para esto son los SAVEPOINT: la transaccion externa queda coherente."""
        with self.db.transaccion():
            self.db.execute("INSERT INTO t VALUES (1)")
            try:
                with self.db.transaccion():
                    self.db.execute("INSERT INTO t VALUES (2)")
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            self.db.execute("INSERT INTO t VALUES (3)")

        valores = [r[0] for r in self.db.execute("SELECT n FROM t ORDER BY n")]
        self.assertEqual(valores, [1, 3], "el 2 debio quedar deshecho, el resto no")

    def test_aguanta_varios_niveles(self):
        with self.db.transaccion():
            with self.db.transaccion():
                with self.db.transaccion():
                    self.db.execute("INSERT INTO t VALUES (1)")

        self.assertEqual(self.contar(), 1)
        self.assertFalse(self.db.en_transaccion)


class AtomicidadDeLasCascadas(unittest.TestCase):
    """Los repositorios que escriben en varias tablas son atomicos por si solos."""

    def setUp(self) -> None:
        self.db = Database(":memory:")
        self.db.connect()
        self.db._connection.executescript(DDL)

    def tearDown(self) -> None:
        self.db.close()

    def _medico(self, n: int, cedula: str):
        from model.medico import Medico

        return Medico(
            cedula_profesional=cedula,
            numero_empleado=f"EMP-{n:04d}",
            departamento="Medicina Interna",
            fecha_ingreso="2015-03-01",
            nombres=f"Nombre{n}",
            apellido_paterno="Paterno",
            direccion_calle="Calle 1",
            codigo_postal="21100",
            ciudad="Mexicali",
            estado="Baja California",
            fecha_nacimiento="1980-01-01",
            genero="Masculino",
            telefono=f"+5268600{n:05d}",
            curp=f"TST{chr(64 + n)}800101HBCNNN0{n}",
        )

    def test_si_falla_el_ultimo_insert_no_queda_nada_a_medias(self):
        """Antes dejaba un DerechoHabiente y un Trabajador huerfanos."""
        from model.repositories import MedicoSQLRepository

        repo = MedicoSQLRepository(self.db)
        repo.registrar(self._medico(1, "1234567"))

        # El segundo choca en el ULTIMO insert, con las dos tablas de arriba ya escritas
        with self.assertRaises(sqlite3.IntegrityError):
            repo.registrar(self._medico(2, "1234567"))

        def contar(tabla):
            return self.db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

        self.assertEqual(contar("Medico"), 1)
        self.assertEqual(contar("Trabajador"), 1, "quedo un trabajador huerfano")
        self.assertEqual(contar("DerechoHabiente"), 1, "quedo una persona huerfana")

    def test_el_controlador_puede_envolver_varias_operaciones(self):
        """La transaccion del repositorio se anida en la del controlador."""
        from model.especialidad import Especialidad
        from model.repositories import EspecialidadSQLRepository, MedicoSQLRepository

        medicos = MedicoSQLRepository(self.db)
        especialidades = EspecialidadSQLRepository(self.db)

        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.transaccion():
                medicos.registrar(self._medico(1, "1234567"))
                especialidades.registrar(Especialidad(nombre="Cardiología"))
                medicos.registrar(self._medico(2, "1234567"))  # cedula repetida

        def contar(tabla):
            return self.db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

        self.assertEqual(contar("Medico"), 0, "la transaccion externa deshace todo")
        self.assertEqual(contar("Especialidad"), 0)
        self.assertEqual(contar("DerechoHabiente"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
