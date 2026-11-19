"""Pruebas de PacienteRepositorio.

Paciente es una especializacion de DerechoHabiente, y en el DDL son dos tablas.
Lo propio de este repositorio es eso: registrar escribe en las dos, leer hace
JOIN, y la baja se delega al DerechoHabiente.
"""

import sqlite3
import unittest

from model.constants import TiposSangre
from model.paciente import Paciente
from model.repositories import PacienteRepositorio, PacienteSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class PacienteTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = PacienteSQLRepository(self.db)

    def nuevo(self, **cambios) -> Paciente:
        datos = self._datos_persona(self._siguiente()) | {"tipo_sangre": "O+"} | cambios
        return Paciente(**datos)


class ContratoDePaciente(ContratoRepositorioMixin, PacienteTestCase):
    """PacienteRepositorio y su implementacion SQL."""

    interfaz = PacienteRepositorio
    implementacion = PacienteSQLRepository

    def test_el_colaborador_comparte_la_misma_base(self):
        self.assertIs(self.repo._dh_repo.db, self.db)


class RegistrarPaciente(PacienteTestCase):
    """registrar(entidad) crea el DerechoHabiente y luego el Paciente."""

    def test_escribe_en_las_dos_tablas(self):
        pac = self.repo.registrar(self.nuevo())

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Paciente"), 1)

    def test_asigna_los_dos_ids(self):
        pac = self.repo.registrar(self.nuevo())

        self.assertEqual(pac.id_derechohabiente, 1)
        self.assertEqual(pac.id_paciente, 1)

    def test_la_fila_de_paciente_apunta_a_su_derechohabiente(self):
        pac = self.repo.registrar(self.nuevo())

        fila = self.leer_fila("Paciente", id_paciente=pac.id_paciente)
        self.assertEqual(fila["id_derechohabiente"], pac.id_derechohabiente)
        self.assertEqual(fila["tipo_sangre"], "O+")

    def test_reutiliza_el_derechohabiente_si_ya_tiene_id(self):
        """Alguien que ya existe como persona no se duplica al volverse paciente."""
        dh = self.crear_derechohabiente()

        pac = self.repo.registrar(
            self.nuevo(
                id_derechohabiente=dh.id_derechohabiente,
                curp=dh.curp,
                telefono=dh.telefono,
            )
        )

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(pac.id_derechohabiente, dh.id_derechohabiente)

    def test_el_tipo_de_sangre_es_opcional(self):
        pac = self.repo.registrar(self.nuevo(tipo_sangre=None))

        self.assertIsNone(self.leer_fila("Paciente", id_paciente=pac.id_paciente)["tipo_sangre"])

    def test_valida_la_entidad_antes_de_escribir(self):
        pac = self.nuevo()
        pac.tipo_sangre = "Z+"
        with self.assertRaises(ValueError):
            self.repo.registrar(pac)
        self.assertEqual(self.contar("Paciente"), 0)
        self.assertEqual(self.contar("DerechoHabiente"), 0)


class ObtenerPacientes(PacienteTestCase):
    """Leer un paciente exige el JOIN con DerechoHabiente."""

    def test_obtener_por_id_trae_los_datos_de_las_dos_tablas(self):
        pac = self.repo.registrar(self.nuevo(nombres="Ana", tipo_sangre="AB-"))

        leido = self.repo.obtener_por_id(pac.id_paciente)

        self.assertIsInstance(leido, Paciente)
        self.assertEqual(leido.nombres, "Ana")  # de DerechoHabiente
        self.assertIs(leido.tipo_sangre, TiposSangre.AB_NEGATIVO)  # de Paciente
        self.assertIsInstance(leido.activo, bool)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_un_derechohabiente_que_no_es_paciente_no_aparece(self):
        self.crear_derechohabiente()

        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_apellidos_y_nombre(self):
        self.repo.registrar(self.nuevo(apellido_paterno="Zamora", apellido_materno="A"))
        self.repo.registrar(self.nuevo(apellido_paterno="Alvarez", apellido_materno="B"))

        apellidos = [p.apellido_paterno for p in self.repo.obtener_todos()]

        self.assertEqual(apellidos, ["Alvarez", "Zamora"])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarPaciente(PacienteTestCase):
    """guardar(entidad) hace upsert de las dos tablas."""

    def test_sin_ids_inserta_en_las_dos_tablas(self):
        pac = self.nuevo()

        self.assertTrue(self.repo.guardar(pac))

        self.assertIsNotNone(pac.id_paciente)
        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Paciente"), 1)

    def test_actualiza_columnas_de_las_dos_tablas(self):
        pac = self.repo.registrar(self.nuevo())

        pac.ciudad = "Tijuana"  # DerechoHabiente
        pac.tipo_sangre = "B+"  # Paciente
        self.assertTrue(self.repo.guardar(pac))

        leido = self.repo.obtener_por_id(pac.id_paciente)
        self.assertEqual(leido.ciudad, "Tijuana")
        self.assertIs(leido.tipo_sangre, TiposSangre.B_POSITIVO)

    def test_no_duplica_filas(self):
        pac = self.repo.registrar(self.nuevo())

        self.repo.guardar(pac)
        self.repo.guardar(pac)

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Paciente"), 1)

    def test_valida_la_entidad_antes_de_escribir(self):
        pac = self.repo.registrar(self.nuevo())
        pac.curp = "NO-ES-CURP"
        with self.assertRaises(ValueError):
            self.repo.guardar(pac)


class DarBajaPaciente(PacienteTestCase):
    """La baja del paciente es la baja de su DerechoHabiente."""

    def test_da_de_baja_al_derechohabiente(self):
        pac = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(pac))

        fila = self.leer_fila("DerechoHabiente", id_derechohabiente=pac.id_derechohabiente)
        self.assertEqual(fila["activo"], 0)

    def test_no_borra_ninguna_de_las_dos_filas(self):
        pac = self.repo.registrar(self.nuevo())

        self.repo.darbaja(pac)

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Paciente"), 1)

    def test_refleja_la_baja_en_la_entidad(self):
        pac = self.repo.registrar(self.nuevo())

        self.repo.darbaja(pac)

        self.assertIs(pac.activo, False)

    def test_busca_el_derechohabiente_si_la_entidad_no_lo_trae(self):
        """Una entidad recien leida de otra via puede traer solo el id_paciente."""
        pac = self.repo.registrar(self.nuevo())

        suelto = self.nuevo(id_paciente=pac.id_paciente, id_derechohabiente=None)
        self.assertTrue(self.repo.darbaja(suelto))

        self.assertEqual(suelto.id_derechohabiente, pac.id_derechohabiente)
        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=pac.id_derechohabiente)["activo"],
            0,
        )

    def test_sin_ningun_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_paciente=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
