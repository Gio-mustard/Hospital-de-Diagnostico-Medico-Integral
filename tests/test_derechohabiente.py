"""Pruebas de DerechoHabienteRepositorio.

Es la raiz de la jerarquia de personas: Paciente, Trabajador, Medico, Enfermero
y Recepcionista heredan de ella y reusan este repositorio para su parte comun.
Su baja es logica (`activo = 0`), no un DELETE.
"""

import sqlite3
import unittest
from datetime import date

from model.constants import Generos
from model.derechohabiente import DerechoHabiente
from model.repositories import (
    DerechoHabienteRepositorio,
    DerechoHabienteSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase


class DerechoHabienteTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = DerechoHabienteSQLRepository(self.db)

    def nuevo(self, **cambios) -> DerechoHabiente:
        return DerechoHabiente(**(self._datos_persona(self._siguiente()) | cambios))


class ContratoDeDerechoHabiente(ContratoRepositorioMixin, DerechoHabienteTestCase):
    """DerechoHabienteRepositorio y su implementacion SQL."""

    interfaz = DerechoHabienteRepositorio
    implementacion = DerechoHabienteSQLRepository


class RegistrarDerechoHabiente(DerechoHabienteTestCase):
    """registrar(entidad) inserta y asigna el id_derechohabiente."""

    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nuevo()).id_derechohabiente, 1)
        self.assertEqual(self.repo.registrar(self.nuevo()).id_derechohabiente, 2)

    def test_devuelve_la_misma_instancia(self):
        dh = self.nuevo()
        self.assertIs(self.repo.registrar(dh), dh)

    def test_deja_la_fila_escrita(self):
        dh = self.repo.registrar(self.nuevo(nombres="Ana", apellido_paterno="Pérez"))

        fila = self.leer_fila("DerechoHabiente", id_derechohabiente=dh.id_derechohabiente)
        self.assertEqual(fila["nombres"], "Ana")
        self.assertEqual(fila["apellido_paterno"], "Pérez")
        self.assertEqual(fila["activo"], 1)

    def test_guarda_el_booleano_activo_como_entero(self):
        """SQLite STRICT no tiene BOOLEAN: la columna es INTEGER con CHECK (0, 1)."""
        dh = self.repo.registrar(self.nuevo(activo=False))

        fila = self.leer_fila("DerechoHabiente", id_derechohabiente=dh.id_derechohabiente)
        self.assertEqual(fila["activo"], 0)
        self.assertIsInstance(fila["activo"], int)

    def test_guarda_la_fecha_de_nacimiento_como_texto_iso(self):
        dh = self.repo.registrar(self.nuevo(fecha_nacimiento=date(1985, 7, 20)))

        fila = self.leer_fila("DerechoHabiente", id_derechohabiente=dh.id_derechohabiente)
        self.assertEqual(fila["fecha_nacimiento"], "1985-07-20")

    def test_el_auth_user_id_es_opcional(self):
        dh = self.repo.registrar(self.nuevo(auth_user_id=None))

        fila = self.leer_fila("DerechoHabiente", id_derechohabiente=dh.id_derechohabiente)
        self.assertIsNone(fila["auth_user_id"])

    def test_la_curp_repetida_choca_con_el_unique(self):
        primero = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(curp=primero.curp))

    def test_valida_la_entidad_antes_de_escribir(self):
        dh = self.nuevo()
        dh.codigo_postal = "ABC"  # el DDL exige 5 digitos
        with self.assertRaises(ValueError):
            self.repo.registrar(dh)
        self.assertEqual(self.contar("DerechoHabiente"), 0)


class ObtenerDerechoHabientes(DerechoHabienteTestCase):
    """Las lecturas devuelven los tipos del dominio."""

    def test_obtener_por_id_reconstruye_la_entidad(self):
        dh = self.repo.registrar(self.nuevo(nombres="Ana"))

        leido = self.repo.obtener_por_id(dh.id_derechohabiente)

        self.assertIsInstance(leido, DerechoHabiente)
        self.assertEqual(leido.nombres, "Ana")

    def test_obtener_por_id_devuelve_bool_y_enum_no_texto(self):
        dh = self.repo.registrar(self.nuevo(genero="Femenino"))

        leido = self.repo.obtener_por_id(dh.id_derechohabiente)

        self.assertIsInstance(leido.activo, bool)
        self.assertIs(leido.activo, True)
        self.assertIs(leido.genero, Generos.FEMENINO)
        self.assertIsInstance(leido.fecha_nacimiento, date)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_ordena_por_apellidos_y_nombre(self):
        self.repo.registrar(self.nuevo(apellido_paterno="Zamora", apellido_materno="A", nombres="Ana"))
        self.repo.registrar(self.nuevo(apellido_paterno="Alvarez", apellido_materno="B", nombres="Beto"))
        self.repo.registrar(self.nuevo(apellido_paterno="Mora", apellido_materno="C", nombres="Carla"))

        apellidos = [d.apellido_paterno for d in self.repo.obtener_todos()]

        self.assertEqual(apellidos, ["Alvarez", "Mora", "Zamora"])

    def test_obtener_todos_incluye_a_los_dados_de_baja(self):
        """La baja es logica: seguir viendolos es lo correcto aqui."""
        dh = self.repo.registrar(self.nuevo())
        self.repo.darbaja(dh)

        self.assertEqual(len(self.repo.obtener_todos()), 1)

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarDerechoHabiente(DerechoHabienteTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        dh = self.nuevo()
        self.assertTrue(self.repo.guardar(dh))
        self.assertIsNotNone(dh.id_derechohabiente)

    def test_con_id_actualiza_sin_duplicar(self):
        dh = self.repo.registrar(self.nuevo())
        dh.ciudad = "Tijuana"

        self.assertTrue(self.repo.guardar(dh))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.repo.obtener_por_id(dh.id_derechohabiente).ciudad, "Tijuana")

    def test_puede_reactivar_a_alguien_dado_de_baja(self):
        dh = self.repo.registrar(self.nuevo())
        self.repo.darbaja(dh)

        dh.activo = True
        self.assertTrue(self.repo.guardar(dh))

        self.assertIs(self.repo.obtener_por_id(dh.id_derechohabiente).activo, True)

    def test_valida_la_entidad_antes_de_escribir(self):
        dh = self.repo.registrar(self.nuevo())
        dh.telefono = "123"  # no es E.164
        with self.assertRaises(ValueError):
            self.repo.guardar(dh)


class DarBajaDerechoHabiente(DerechoHabienteTestCase):
    """Baja logica: la fila se queda y solo pasa activo a 0."""

    def test_pone_activo_en_cero_sin_borrar_la_fila(self):
        dh = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(dh))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=dh.id_derechohabiente)["activo"],
            0,
        )

    def test_refleja_la_baja_en_la_entidad_recibida(self):
        dh = self.repo.registrar(self.nuevo())

        self.repo.darbaja(dh)

        self.assertIs(dh.activo, False)

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_derechohabiente=9999)))

    def test_dar_de_baja_dos_veces_es_inofensivo(self):
        dh = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(dh))
        self.assertTrue(self.repo.darbaja(dh))
        self.assertIs(dh.activo, False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
