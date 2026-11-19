"""Pruebas de AtencionMedicaRepositorio.

Fachada sin tabla propia: despacha a CitaSQLRepository o a
IngresoEmergenciaSQLRepository segun el tipo de la entidad. Lo que se prueba es
el despacho y que cada operacion caiga en la tabla correcta.
"""

import unittest

from model.atencion_medica import AtencionMedica
from model.cita import Cita
from model.constants import EstadosCita
from model.ingreso_emergencia import IngresoEmergencia
from model.repositories import (
    AtencionMedicaRepositorio,
    AtencionMedicaSQLRepository,
    CitaSQLRepository,
    IngresoEmergenciaSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase


class AtencionMedicaTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = AtencionMedicaSQLRepository(self.db)

    def _comunes(self) -> dict:
        return {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
        }

    def nueva_cita(self, **cambios) -> Cita:
        datos = (
            self._comunes()
            | {"fecha_hora": "2026-12-01 10:30:00", "motivo": "Dolor abdominal"}
            | cambios
        )
        return Cita(**datos)

    def nueva_emergencia(self, **cambios) -> IngresoEmergencia:
        datos = (
            self._comunes()
            | {
                "fecha_hora": "2026-12-01 03:15:00",
                "motivo": "Dolor torácico",
                "nivel_urgencia": "Alto",
            }
            | cambios
        )
        return IngresoEmergencia(**datos)


class ContratoDeAtencionMedica(ContratoRepositorioMixin, AtencionMedicaTestCase):
    """AtencionMedicaRepositorio y su implementacion SQL."""

    interfaz = AtencionMedicaRepositorio
    implementacion = AtencionMedicaSQLRepository


class DespachoDeLaFachada(AtencionMedicaTestCase):
    """Cada entidad tiene que acabar en el repositorio que le toca."""

    def test_los_colaboradores_comparten_la_misma_base(self):
        self.assertIs(self.repo._cita_repo.db, self.db)
        self.assertIs(self.repo._emergencia_repo.db, self.db)

    def test_una_cita_va_al_repositorio_de_citas(self):
        self.assertIsInstance(self.repo._repo_de(self.nueva_cita()), CitaSQLRepository)

    def test_una_emergencia_va_al_repositorio_de_emergencias(self):
        self.assertIsInstance(
            self.repo._repo_de(self.nueva_emergencia()), IngresoEmergenciaSQLRepository
        )

    def test_otra_cosa_es_un_error_de_tipo(self):
        with self.assertRaises(TypeError):
            self.repo._repo_de(self.paciente)


class EscribirPorLaFachada(AtencionMedicaTestCase):
    def test_registrar_una_cita_solo_toca_la_tabla_Cita(self):
        cita = self.repo.registrar(self.nueva_cita())

        self.assertEqual(cita.id_cita, 1)
        self.assertEqual(self.contar("Cita"), 1)
        self.assertEqual(self.contar("IngresoEmergencia"), 0)

    def test_registrar_una_emergencia_solo_toca_su_tabla(self):
        emergencia = self.repo.registrar(self.nueva_emergencia())

        self.assertEqual(emergencia.id_ingreso_emergencia, 1)
        self.assertEqual(self.contar("IngresoEmergencia"), 1)
        self.assertEqual(self.contar("Cita"), 0)

    def test_guardar_actualiza_en_la_tabla_correcta(self):
        emergencia = self.repo.registrar(self.nueva_emergencia())
        emergencia.diagnostico = "Infarto agudo"

        self.assertTrue(self.repo.guardar(emergencia))

        fila = self.leer_fila(
            "IngresoEmergencia", id_ingreso_emergencia=emergencia.id_ingreso_emergencia
        )
        self.assertEqual(fila["diagnostico"], "Infarto agudo")

    def test_darbaja_de_una_cita_la_cancela(self):
        cita = self.repo.registrar(self.nueva_cita())

        self.assertTrue(self.repo.darbaja(cita))

        self.assertEqual(self.leer_fila("Cita", id_cita=cita.id_cita)["estado"], "Cancelada")

    def test_darbaja_de_una_emergencia_la_borra(self):
        emergencia = self.repo.registrar(self.nueva_emergencia())

        self.assertTrue(self.repo.darbaja(emergencia))

        self.assertEqual(self.contar("IngresoEmergencia"), 0)

    def test_propaga_la_regla_de_no_cancelar_una_cita_completada(self):
        """La fachada no se salta las reglas del repositorio al que delega."""
        cita = self.repo.registrar(
            self.nueva_cita(estado=EstadosCita.COMPLETADA, diagnostico="Gastritis")
        )

        with self.assertRaises(ValueError):
            self.repo.darbaja(cita)


class LeerPorLaFachada(AtencionMedicaTestCase):
    """obtener_por_id necesita la bandera: los dos ids son PK distintas."""

    def test_obtener_por_id_lee_citas_por_defecto(self):
        self.repo.registrar(self.nueva_cita())
        self.repo.registrar(self.nueva_emergencia())

        self.assertIsInstance(self.repo.obtener_por_id(1), Cita)

    def test_obtener_por_id_con_la_bandera_lee_emergencias(self):
        self.repo.registrar(self.nueva_cita())
        self.repo.registrar(self.nueva_emergencia())

        self.assertIsInstance(
            self.repo.obtener_por_id(1, es_emergencia=True), IngresoEmergencia
        )

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))
        self.assertIsNone(self.repo.obtener_por_id(9999, es_emergencia=True))

    def test_obtener_todos_junta_citas_y_emergencias(self):
        self.repo.registrar(self.nueva_cita())
        self.repo.registrar(self.nueva_emergencia())

        todas = self.repo.obtener_todos()

        self.assertEqual(len(todas), 2)
        self.assertTrue(all(isinstance(a, AtencionMedica) for a in todas))
        self.assertEqual(
            [type(a).__name__ for a in todas], ["Cita", "IngresoEmergencia"]
        )

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
