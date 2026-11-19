"""Pruebas de EnfermeroRepositorio.

Mismo esquema que Medico: DerechoHabiente -> Trabajador -> Enfermero, con la
diferencia de que la tabla Enfermero no agrega columnas propias mas alla de
`activo`.
"""

import sqlite3
import unittest

from model.enfermero import Enfermero
from model.repositories import EnfermeroRepositorio, EnfermeroSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class EnfermeroTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = EnfermeroSQLRepository(self.db)

    def nuevo(self, **cambios) -> Enfermero:
        n = self._siguiente()
        datos = self._datos_persona(n) | self._datos_trabajador(n) | cambios
        return Enfermero(**datos)


class ContratoDeEnfermero(ContratoRepositorioMixin, EnfermeroTestCase):
    """EnfermeroRepositorio y su implementacion SQL."""

    interfaz = EnfermeroRepositorio
    implementacion = EnfermeroSQLRepository

    def test_el_colaborador_comparte_la_misma_base(self):
        self.assertIs(self.repo._trab_repo.db, self.db)


class RegistrarEnfermero(EnfermeroTestCase):
    def test_escribe_en_las_tres_tablas(self):
        self.repo.registrar(self.nuevo())

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("Enfermero"), 1)

    def test_asigna_los_tres_ids(self):
        enf = self.repo.registrar(self.nuevo())

        self.assertEqual(enf.id_derechohabiente, 1)
        self.assertEqual(enf.id_trabajador, 1)
        self.assertEqual(enf.id_enfermero, 1)

    def test_la_fila_apunta_a_su_trabajador(self):
        enf = self.repo.registrar(self.nuevo())

        fila = self.leer_fila("Enfermero", id_enfermero=enf.id_enfermero)
        self.assertEqual(fila["id_trabajador"], enf.id_trabajador)
        self.assertEqual(fila["activo"], 1)

    def test_reutiliza_el_trabajador_si_ya_tiene_id(self):
        trab = self.crear_trabajador()

        enf = self.repo.registrar(
            self.nuevo(
                id_trabajador=trab.id_trabajador,
                id_derechohabiente=trab.id_derechohabiente,
                curp=trab.curp,
                telefono=trab.telefono,
                numero_empleado=trab.numero_empleado,
            )
        )

        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(enf.id_trabajador, trab.id_trabajador)

    def test_un_trabajador_no_puede_ser_enfermero_dos_veces(self):
        """id_trabajador es UNIQUE en la tabla Enfermero."""
        enf = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(
                self.nuevo(
                    id_trabajador=enf.id_trabajador,
                    id_derechohabiente=enf.id_derechohabiente,
                    curp=enf.curp,
                    telefono=enf.telefono,
                    numero_empleado=enf.numero_empleado,
                )
            )

    def test_valida_la_entidad_antes_de_escribir(self):
        enf = self.nuevo()
        enf.numero_empleado = "X"
        with self.assertRaises(ValueError):
            self.repo.registrar(enf)
        self.assertEqual(self.contar("Enfermero"), 0)


class ObtenerEnfermeros(EnfermeroTestCase):
    def test_obtener_por_id_trae_los_datos_de_las_tres_tablas(self):
        enf = self.repo.registrar(self.nuevo(nombres="Lucía", departamento="Urgencias"))

        leido = self.repo.obtener_por_id(enf.id_enfermero)

        self.assertIsInstance(leido, Enfermero)
        self.assertEqual(leido.nombres, "Lucía")  # DerechoHabiente
        self.assertEqual(leido.departamento, "Urgencias")  # Trabajador
        self.assertEqual(leido.id_enfermero, enf.id_enfermero)  # Enfermero
        self.assertIsInstance(leido.activo, bool)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_un_trabajador_que_no_es_enfermero_no_aparece(self):
        self.crear_trabajador()
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_apellidos_y_nombre(self):
        self.repo.registrar(self.nuevo(apellido_paterno="Zamora", apellido_materno="A"))
        self.repo.registrar(self.nuevo(apellido_paterno="Alvarez", apellido_materno="B"))

        apellidos = [e.apellido_paterno for e in self.repo.obtener_todos()]

        self.assertEqual(apellidos, ["Alvarez", "Zamora"])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarEnfermero(EnfermeroTestCase):
    def test_sin_ids_inserta_en_las_tres_tablas(self):
        enf = self.nuevo()

        self.assertTrue(self.repo.guardar(enf))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("Enfermero"), 1)

    def test_actualiza_columnas_de_los_niveles_de_arriba(self):
        enf = self.repo.registrar(self.nuevo())

        enf.ciudad = "Tecate"
        enf.departamento = "Pediatría"
        self.assertTrue(self.repo.guardar(enf))

        leido = self.repo.obtener_por_id(enf.id_enfermero)
        self.assertEqual(leido.ciudad, "Tecate")
        self.assertEqual(leido.departamento, "Pediatría")

    def test_no_duplica_filas(self):
        enf = self.repo.registrar(self.nuevo())

        self.repo.guardar(enf)
        self.repo.guardar(enf)

        self.assertEqual(self.contar("Enfermero"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_valida_la_entidad_antes_de_escribir(self):
        enf = self.repo.registrar(self.nuevo())
        enf.departamento = "   "
        with self.assertRaises(ValueError):
            self.repo.guardar(enf)


class DarBajaEnfermero(EnfermeroTestCase):
    def test_da_de_baja_en_las_tres_tablas(self):
        enf = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(enf))

        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=enf.id_derechohabiente)["activo"],
            0,
        )
        self.assertEqual(
            self.leer_fila("Trabajador", id_trabajador=enf.id_trabajador)["activo"], 0
        )
        self.assertEqual(
            self.leer_fila("Enfermero", id_enfermero=enf.id_enfermero)["activo"], 0
        )

    def test_no_borra_ninguna_fila(self):
        enf = self.repo.registrar(self.nuevo())

        self.repo.darbaja(enf)

        self.assertEqual(self.contar("Enfermero"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_completa_los_ids_que_la_entidad_no_trae(self):
        enf = self.repo.registrar(self.nuevo())

        suelto = self.nuevo(
            id_enfermero=enf.id_enfermero, id_trabajador=None, id_derechohabiente=None
        )
        self.assertTrue(self.repo.darbaja(suelto))

        self.assertEqual(suelto.id_trabajador, enf.id_trabajador)
        self.assertEqual(suelto.id_derechohabiente, enf.id_derechohabiente)

    def test_sin_ningun_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_enfermero=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
