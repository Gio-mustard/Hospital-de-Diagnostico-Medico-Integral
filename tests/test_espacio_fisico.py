"""Pruebas de EspacioFisicoRepositorio.

Es una fachada: no tiene tabla propia. Despacha a HabitacionSQLRepository o a
ConsultorioSQLRepository segun el tipo de la entidad que recibe, asi que lo que
hay que probar es el despacho, no el SQL (ese ya se prueba en los modulos de
cada uno).
"""

import unittest

from model.consultorio import Consultorio
from model.espacio_fisico import EspacioFisico
from model.habitacion import Habitacion
from model.repositories import (
    ConsultorioSQLRepository,
    EspacioFisicoRepositorio,
    EspacioFisicoSQLRepository,
    HabitacionSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase


class EspacioFisicoTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = EspacioFisicoSQLRepository(self.db)

    def nueva_habitacion(self, **cambios) -> Habitacion:
        return Habitacion(
            **(
                {
                    "num_habitacion": 101,
                    "piso": 1,
                    "tipo": "Individual",
                    "estado": "Disponible",
                }
                | cambios
            )
        )

    def nuevo_consultorio(self, **cambios) -> Consultorio:
        return Consultorio(
            **(
                {
                    "num_consultorio": 5,
                    "piso": 2,
                    "departamento": "Medicina Interna",
                    "estado": "Disponible",
                }
                | cambios
            )
        )


class ContratoDeEspacioFisico(ContratoRepositorioMixin, EspacioFisicoTestCase):
    """EspacioFisicoRepositorio y su implementacion SQL."""

    interfaz = EspacioFisicoRepositorio
    implementacion = EspacioFisicoSQLRepository


class DespachoDeLaFachada(EspacioFisicoTestCase):
    """Cada entidad tiene que acabar en el repositorio que le toca."""

    def test_los_colaboradores_comparten_la_misma_base(self):
        self.assertIs(self.repo._hab_repo.db, self.db)
        self.assertIs(self.repo._cons_repo.db, self.db)

    def test_una_habitacion_va_al_repositorio_de_habitaciones(self):
        self.assertIsInstance(
            self.repo._repo_de(self.nueva_habitacion()), HabitacionSQLRepository
        )

    def test_un_consultorio_va_al_repositorio_de_consultorios(self):
        self.assertIsInstance(
            self.repo._repo_de(self.nuevo_consultorio()), ConsultorioSQLRepository
        )

    def test_otra_cosa_es_un_error_de_tipo(self):
        with self.assertRaises(TypeError):
            self.repo._repo_de(self.paciente)


class EscribirPorLaFachada(EspacioFisicoTestCase):
    """registrar / guardar / darbaja delegan y conservan el efecto."""

    def test_registrar_una_habitacion(self):
        hab = self.repo.registrar(self.nueva_habitacion())

        self.assertEqual(hab.num_habitacion, 101)
        self.assertIsNotNone(self.leer_fila("Habitacion", num_habitacion=101))
        self.assertEqual(self.contar("Consultorio"), 0)

    def test_registrar_un_consultorio(self):
        cons = self.repo.registrar(self.nuevo_consultorio())

        self.assertEqual(cons.num_consultorio, 5)
        self.assertIsNotNone(self.leer_fila("Consultorio", num_consultorio=5))
        self.assertEqual(self.contar("Habitacion"), 0)

    def test_guardar_actualiza_en_la_tabla_correcta(self):
        hab = self.repo.registrar(self.nueva_habitacion())
        hab.estado = "Ocupada"

        self.assertTrue(self.repo.guardar(hab))

        self.assertEqual(
            self.leer_fila("Habitacion", num_habitacion=101)["estado"], "Ocupada"
        )

    def test_darbaja_borra_en_la_tabla_correcta(self):
        hab = self.repo.registrar(self.nueva_habitacion())
        cons = self.repo.registrar(self.nuevo_consultorio())

        self.assertTrue(self.repo.darbaja(cons))

        self.assertEqual(self.contar("Consultorio"), 0)
        self.assertEqual(self.contar("Habitacion"), 1, "no debio tocar las habitaciones")
        self.assertIsNotNone(self.repo.obtener_por_id(hab.num_habitacion))


class LeerPorLaFachada(EspacioFisicoTestCase):
    """obtener_por_id necesita la bandera, porque los dos numeros son PK distintas."""

    def test_obtener_por_id_lee_habitaciones_por_defecto(self):
        self.repo.registrar(self.nueva_habitacion(num_habitacion=7))
        self.repo.registrar(self.nuevo_consultorio(num_consultorio=7))

        self.assertIsInstance(self.repo.obtener_por_id(7), Habitacion)

    def test_obtener_por_id_con_la_bandera_lee_consultorios(self):
        self.repo.registrar(self.nueva_habitacion(num_habitacion=7))
        self.repo.registrar(self.nuevo_consultorio(num_consultorio=7))

        self.assertIsInstance(
            self.repo.obtener_por_id(7, es_consultorio=True), Consultorio
        )

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))
        self.assertIsNone(self.repo.obtener_por_id(9999, es_consultorio=True))

    def test_obtener_todos_junta_los_dos_tipos(self):
        self.repo.registrar(self.nueva_habitacion())
        self.repo.registrar(self.nuevo_consultorio())

        todos = self.repo.obtener_todos()

        self.assertEqual(len(todos), 2)
        self.assertTrue(all(isinstance(e, EspacioFisico) for e in todos))
        self.assertEqual(
            [type(e).__name__ for e in todos], ["Habitacion", "Consultorio"]
        )

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
