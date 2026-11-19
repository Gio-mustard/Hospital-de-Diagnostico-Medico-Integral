"""Pruebas de RecepcionistaRepositorio.

A diferencia de Medico y Enfermero, Recepcionista cuelga directo de
DerechoHabiente: su `id_trabajador` es una FK opcional, no el camino por el que
se construye.
"""

import sqlite3
import unittest

from model.constants import Turnos
from model.recepcionista import Recepcionista
from model.repositories import RecepcionistaRepositorio, RecepcionistaSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class RecepcionistaTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = RecepcionistaSQLRepository(self.db)

    def nueva(self, **cambios) -> Recepcionista:
        n = self._siguiente()
        return Recepcionista(**(self._datos_persona(n) | cambios))


class ContratoDeRecepcionista(ContratoRepositorioMixin, RecepcionistaTestCase):
    """RecepcionistaRepositorio y su implementacion SQL."""

    interfaz = RecepcionistaRepositorio
    implementacion = RecepcionistaSQLRepository

    def test_el_colaborador_comparte_la_misma_base(self):
        self.assertIs(self.repo._dh_repo.db, self.db)


class RegistrarRecepcionista(RecepcionistaTestCase):
    def test_escribe_en_las_dos_tablas(self):
        self.repo.registrar(self.nueva())

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Recepcionista"), 1)

    def test_asigna_los_dos_ids(self):
        recep = self.repo.registrar(self.nueva())

        self.assertEqual(recep.id_derechohabiente, 1)
        self.assertEqual(recep.id_recepcionista, 1)

    def test_usa_los_valores_por_defecto_del_turno_y_el_modulo(self):
        recep = self.repo.registrar(self.nueva())

        fila = self.leer_fila("Recepcionista", id_recepcionista=recep.id_recepcionista)
        self.assertEqual(fila["turno"], "Matutino")
        self.assertEqual(fila["modulo_atencion"], "Admisión Principal")
        self.assertEqual(fila["activo"], 1)

    def test_guarda_el_turno_como_texto(self):
        recep = self.repo.registrar(self.nueva(turno=Turnos.NOCTURNO))

        fila = self.leer_fila("Recepcionista", id_recepcionista=recep.id_recepcionista)
        self.assertEqual(fila["turno"], "Nocturno")

    def test_el_id_trabajador_es_opcional(self):
        recep = self.repo.registrar(self.nueva())

        fila = self.leer_fila("Recepcionista", id_recepcionista=recep.id_recepcionista)
        self.assertIsNone(fila["id_trabajador"])

    def test_puede_apuntar_a_un_trabajador_existente(self):
        trab = self.crear_trabajador()

        recep = self.repo.registrar(
            self.nueva(
                id_trabajador=trab.id_trabajador,
                id_derechohabiente=trab.id_derechohabiente,
                curp=trab.curp,
                telefono=trab.telefono,
            )
        )

        fila = self.leer_fila("Recepcionista", id_recepcionista=recep.id_recepcionista)
        self.assertEqual(fila["id_trabajador"], trab.id_trabajador)

    def test_valida_la_entidad_antes_de_escribir(self):
        recep = self.nueva()
        recep.turno = "Madrugada"  # no esta en el enum Turnos
        with self.assertRaises(ValueError):
            self.repo.registrar(recep)
        self.assertEqual(self.contar("Recepcionista"), 0)


class ObtenerRecepcionistas(RecepcionistaTestCase):
    def test_obtener_por_id_trae_los_datos_de_las_dos_tablas(self):
        recep = self.repo.registrar(
            self.nueva(nombres="Marta", modulo_atencion="Urgencias")
        )

        leida = self.repo.obtener_por_id(recep.id_recepcionista)

        self.assertIsInstance(leida, Recepcionista)
        self.assertEqual(leida.nombres, "Marta")  # DerechoHabiente
        self.assertEqual(leida.modulo_atencion, "Urgencias")  # Recepcionista
        self.assertIs(leida.turno, Turnos.MATUTINO)
        self.assertIsInstance(leida.activo, bool)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_un_derechohabiente_que_no_es_recepcionista_no_aparece(self):
        self.crear_derechohabiente()
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_turno_y_luego_por_nombre(self):
        self.repo.registrar(self.nueva(turno="Nocturno", apellido_paterno="Alvarez"))
        self.repo.registrar(self.nueva(turno="Matutino", apellido_paterno="Zamora"))

        turnos = [r.turno for r in self.repo.obtener_todos()]

        # 'Matutino' < 'Nocturno' como texto, que es como ordena el SQL
        self.assertEqual(turnos, [Turnos.MATUTINO, Turnos.NOCTURNO])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarRecepcionista(RecepcionistaTestCase):
    def test_sin_ids_inserta_en_las_dos_tablas(self):
        recep = self.nueva()

        self.assertTrue(self.repo.guardar(recep))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Recepcionista"), 1)

    def test_actualiza_columnas_de_las_dos_tablas(self):
        recep = self.repo.registrar(self.nueva())

        recep.ciudad = "Rosarito"  # DerechoHabiente
        recep.turno = Turnos.VESPERTINO  # Recepcionista
        self.assertTrue(self.repo.guardar(recep))

        leida = self.repo.obtener_por_id(recep.id_recepcionista)
        self.assertEqual(leida.ciudad, "Rosarito")
        self.assertIs(leida.turno, Turnos.VESPERTINO)

    def test_no_duplica_filas(self):
        recep = self.repo.registrar(self.nueva())

        self.repo.guardar(recep)
        self.repo.guardar(recep)

        self.assertEqual(self.contar("Recepcionista"), 1)

    def test_valida_la_entidad_antes_de_escribir(self):
        recep = self.repo.registrar(self.nueva())
        recep.extension_tel = "12345678901234"  # pasa de 10 caracteres
        with self.assertRaises(ValueError):
            self.repo.guardar(recep)


class DarBajaRecepcionista(RecepcionistaTestCase):
    """Baja logica en DerechoHabiente y en la propia tabla."""

    def test_da_de_baja_en_las_dos_tablas(self):
        recep = self.repo.registrar(self.nueva())

        self.assertTrue(self.repo.darbaja(recep))

        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=recep.id_derechohabiente)["activo"],
            0,
        )
        self.assertEqual(
            self.leer_fila("Recepcionista", id_recepcionista=recep.id_recepcionista)["activo"],
            0,
        )

    def test_no_borra_ninguna_fila(self):
        recep = self.repo.registrar(self.nueva())

        self.repo.darbaja(recep)

        self.assertEqual(self.contar("Recepcionista"), 1)
        self.assertEqual(self.contar("DerechoHabiente"), 1)

    def test_refleja_la_baja_en_la_entidad(self):
        recep = self.repo.registrar(self.nueva())

        self.repo.darbaja(recep)

        self.assertIs(recep.activo, False)

    def test_busca_el_derechohabiente_si_la_entidad_no_lo_trae(self):
        recep = self.repo.registrar(self.nueva())

        suelta = self.nueva(
            id_recepcionista=recep.id_recepcionista, id_derechohabiente=None
        )
        self.assertTrue(self.repo.darbaja(suelta))

        self.assertEqual(suelta.id_derechohabiente, recep.id_derechohabiente)

    def test_sin_ningun_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva(id_recepcionista=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
