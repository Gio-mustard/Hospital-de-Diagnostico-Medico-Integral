"""Pruebas de TrabajadorRepositorio.

Trabajador es DerechoHabiente + datos de empleo. Es el eslabon intermedio: de
el heredan Medico y Enfermero, que reusan este repositorio igual que este reusa
el de DerechoHabiente.
"""

import sqlite3
import unittest
from datetime import date

from model.repositories import TrabajadorRepositorio, TrabajadorSQLRepository
from model.trabajador import Trabajador

from .base import ContratoRepositorioMixin, RepositorioTestCase


class TrabajadorTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = TrabajadorSQLRepository(self.db)

    def nuevo(self, **cambios) -> Trabajador:
        n = self._siguiente()
        return Trabajador(**(self._datos_persona(n) | self._datos_trabajador(n) | cambios))


class ContratoDeTrabajador(ContratoRepositorioMixin, TrabajadorTestCase):
    """TrabajadorRepositorio y su implementacion SQL."""

    interfaz = TrabajadorRepositorio
    implementacion = TrabajadorSQLRepository

    def test_el_colaborador_comparte_la_misma_base(self):
        self.assertIs(self.repo._dh_repo.db, self.db)


class RegistrarTrabajador(TrabajadorTestCase):
    def test_escribe_en_las_dos_tablas(self):
        self.repo.registrar(self.nuevo())

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_asigna_los_dos_ids(self):
        trab = self.repo.registrar(self.nuevo())

        self.assertEqual(trab.id_derechohabiente, 1)
        self.assertEqual(trab.id_trabajador, 1)

    def test_deja_la_fila_escrita(self):
        trab = self.repo.registrar(
            self.nuevo(departamento="Urgencias", fecha_ingreso=date(2020, 6, 1))
        )

        fila = self.leer_fila("Trabajador", id_trabajador=trab.id_trabajador)
        self.assertEqual(fila["departamento"], "Urgencias")
        self.assertEqual(fila["fecha_ingreso"], "2020-06-01")
        self.assertEqual(fila["activo"], 1)

    def test_reutiliza_el_derechohabiente_si_ya_tiene_id(self):
        dh = self.crear_derechohabiente()

        trab = self.repo.registrar(
            self.nuevo(
                id_derechohabiente=dh.id_derechohabiente,
                curp=dh.curp,
                telefono=dh.telefono,
            )
        )

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(trab.id_derechohabiente, dh.id_derechohabiente)

    def test_el_numero_de_empleado_repetido_choca_con_el_unique(self):
        primero = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(numero_empleado=primero.numero_empleado))

    def test_valida_la_entidad_antes_de_escribir(self):
        trab = self.nuevo()
        trab.numero_empleado = "12345"  # el DDL exige el prefijo EMP-
        with self.assertRaises(ValueError):
            self.repo.registrar(trab)
        self.assertEqual(self.contar("Trabajador"), 0)


class ObtenerTrabajadores(TrabajadorTestCase):
    def test_obtener_por_id_trae_los_datos_de_las_dos_tablas(self):
        trab = self.repo.registrar(self.nuevo(nombres="Luis", departamento="Urgencias"))

        leido = self.repo.obtener_por_id(trab.id_trabajador)

        self.assertIsInstance(leido, Trabajador)
        self.assertEqual(leido.nombres, "Luis")  # de DerechoHabiente
        self.assertEqual(leido.departamento, "Urgencias")  # de Trabajador
        self.assertIsInstance(leido.fecha_ingreso, date)
        self.assertIsInstance(leido.activo, bool)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_un_derechohabiente_que_no_es_trabajador_no_aparece(self):
        self.crear_derechohabiente()
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_numero_de_empleado(self):
        self.repo.registrar(self.nuevo(numero_empleado="EMP-0030"))
        self.repo.registrar(self.nuevo(numero_empleado="EMP-0010"))
        self.repo.registrar(self.nuevo(numero_empleado="EMP-0020"))

        numeros = [t.numero_empleado for t in self.repo.obtener_todos()]

        self.assertEqual(numeros, ["EMP-0010", "EMP-0020", "EMP-0030"])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarTrabajador(TrabajadorTestCase):
    def test_sin_ids_inserta_en_las_dos_tablas(self):
        trab = self.nuevo()

        self.assertTrue(self.repo.guardar(trab))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_actualiza_columnas_de_las_dos_tablas(self):
        trab = self.repo.registrar(self.nuevo())

        trab.ciudad = "Ensenada"  # DerechoHabiente
        trab.departamento = "Pediatría"  # Trabajador
        self.assertTrue(self.repo.guardar(trab))

        leido = self.repo.obtener_por_id(trab.id_trabajador)
        self.assertEqual(leido.ciudad, "Ensenada")
        self.assertEqual(leido.departamento, "Pediatría")

    def test_no_duplica_filas(self):
        trab = self.repo.registrar(self.nuevo())

        self.repo.guardar(trab)
        self.repo.guardar(trab)

        self.assertEqual(self.contar("Trabajador"), 1)

    def test_valida_la_entidad_antes_de_escribir(self):
        trab = self.repo.registrar(self.nuevo())
        trab.departamento = ""
        with self.assertRaises(ValueError):
            self.repo.guardar(trab)


class DarBajaTrabajador(TrabajadorTestCase):
    """Baja logica en cascada: DerechoHabiente y la propia tabla."""

    def test_da_de_baja_en_las_dos_tablas(self):
        trab = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(trab))

        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=trab.id_derechohabiente)["activo"],
            0,
        )
        self.assertEqual(
            self.leer_fila("Trabajador", id_trabajador=trab.id_trabajador)["activo"], 0
        )

    def test_no_borra_ninguna_fila(self):
        trab = self.repo.registrar(self.nuevo())

        self.repo.darbaja(trab)

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_refleja_la_baja_en_la_entidad(self):
        trab = self.repo.registrar(self.nuevo())

        self.repo.darbaja(trab)

        self.assertIs(trab.activo, False)

    def test_busca_el_derechohabiente_si_la_entidad_no_lo_trae(self):
        trab = self.repo.registrar(self.nuevo())

        suelto = self.nuevo(id_trabajador=trab.id_trabajador, id_derechohabiente=None)
        self.assertTrue(self.repo.darbaja(suelto))

        self.assertEqual(suelto.id_derechohabiente, trab.id_derechohabiente)

    def test_sin_ningun_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_trabajador=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
