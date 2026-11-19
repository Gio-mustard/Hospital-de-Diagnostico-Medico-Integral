"""Pruebas de HistorialMedicoRepositorio.

Dos cosas propias de esta tabla:

1. Dos columnas JSON: `datos_dinamicos` (objeto) y `etiquetas` (arreglo). El
   repositorio las serializa al escribir y las deserializa al leer.
2. `uuid_publico` lo genera la base con un DEFAULT. El repositorio lo omite
   cuando viene vacio, para no pisarlo con NULL ni en el INSERT ni en el UPDATE.
"""

import json
import sqlite3
import unittest
from datetime import datetime

from model.constants import TiposDocumento
from model.historial_medico import HistorialMedico
from model.repositories import (
    HistorialMedicoRepositorio,
    HistorialMedicoSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase

URL = "https://archivos.hospital.com/expediente-1.pdf"


class HistorialMedicoTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = HistorialMedicoSQLRepository(self.db)

    def nuevo(self, **cambios) -> HistorialMedico:
        datos = {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
            "fecha_registro": "2026-12-01 09:00:00",
            "documento_url": URL,
        } | cambios
        return HistorialMedico(**datos)


class ContratoDeHistorialMedico(ContratoRepositorioMixin, HistorialMedicoTestCase):
    """HistorialMedicoRepositorio y su implementacion SQL."""

    interfaz = HistorialMedicoRepositorio
    implementacion = HistorialMedicoSQLRepository


class RegistrarHistorialMedico(HistorialMedicoTestCase):
    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nuevo()).id_historial, 1)
        self.assertEqual(self.repo.registrar(self.nuevo()).id_historial, 2)

    def test_devuelve_la_misma_instancia(self):
        historial = self.nuevo()
        self.assertIs(self.repo.registrar(historial), historial)

    def test_la_base_genera_el_uuid_publico_cuando_no_se_manda(self):
        historial = self.repo.registrar(self.nuevo())

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertIsNotNone(fila["uuid_publico"])
        self.assertEqual(len(fila["uuid_publico"]), 36, "UUID con guiones")

    def test_dos_historiales_reciben_uuids_distintos(self):
        primero = self.repo.registrar(self.nuevo())
        segundo = self.repo.registrar(self.nuevo())

        uuid_1 = self.leer_fila("HistorialMedico", id_historial=primero.id_historial)["uuid_publico"]
        uuid_2 = self.leer_fila("HistorialMedico", id_historial=segundo.id_historial)["uuid_publico"]

        self.assertNotEqual(uuid_1, uuid_2)

    def test_usa_el_tipo_de_documento_por_defecto(self):
        historial = self.repo.registrar(self.nuevo())

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertEqual(fila["tipo_documento"], "Expediente PDF")

    def test_guarda_los_dos_campos_json(self):
        historial = self.repo.registrar(
            self.nuevo(
                datos_dinamicos={"presion": "120/80", "pulso": 72},
                etiquetas=["urgente", "cardio"],
            )
        )

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertEqual(json.loads(fila["datos_dinamicos"]), {"presion": "120/80", "pulso": 72})
        self.assertEqual(json.loads(fila["etiquetas"]), ["urgente", "cardio"])

    def test_las_etiquetas_vacias_se_guardan_como_arreglo_json(self):
        historial = self.repo.registrar(self.nuevo())

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertEqual(fila["etiquetas"], "[]")

    def test_guarda_la_fecha_con_el_formato_del_ddl(self):
        historial = self.repo.registrar(
            self.nuevo(fecha_registro=datetime(2026, 12, 1, 9, 0))
        )

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertEqual(fila["fecha_registro"], "2026-12-01 09:00:00")

    def test_puede_no_tener_url_si_trae_datos_dinamicos(self):
        """chk_hist_no_vacio: o una cosa o la otra, pero algo."""
        historial = self.repo.registrar(
            self.nuevo(documento_url=None, datos_dinamicos={"peso": 70})
        )

        fila = self.leer_fila("HistorialMedico", id_historial=historial.id_historial)
        self.assertIsNone(fila["documento_url"])

    def test_no_puede_estar_vacio_de_las_dos_cosas(self):
        with self.assertRaises(ValueError):
            self.nuevo(documento_url=None, datos_dinamicos=None)

    def test_la_url_tiene_que_ser_https(self):
        with self.assertRaises(ValueError):
            self.nuevo(documento_url="http://insegura.com/x.pdf")

    def test_valida_la_entidad_antes_de_escribir(self):
        historial = self.nuevo()
        historial.tipo_documento = "Inventado"
        with self.assertRaises(ValueError):
            self.repo.registrar(historial)
        self.assertEqual(self.contar("HistorialMedico"), 0)

    def test_una_fk_inexistente_falla_en_la_base(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(id_paciente=9999))


class ObtenerHistorialesMedicos(HistorialMedicoTestCase):
    """Al leer, los JSON vuelven a ser dict y list."""

    def test_obtener_por_id_deserializa_los_dos_json(self):
        historial = self.repo.registrar(
            self.nuevo(datos_dinamicos={"pulso": 72}, etiquetas=["cardio"])
        )

        leido = self.repo.obtener_por_id(historial.id_historial)

        self.assertIsInstance(leido, HistorialMedico)
        self.assertIsInstance(leido.datos_dinamicos, dict)
        self.assertEqual(leido.datos_dinamicos, {"pulso": 72})
        self.assertIsInstance(leido.etiquetas, list)
        self.assertEqual(leido.etiquetas, ["cardio"])

    def test_obtener_por_id_devuelve_los_tipos_del_dominio(self):
        historial = self.repo.registrar(
            self.nuevo(tipo_documento=TiposDocumento.LABORATORIO)
        )

        leido = self.repo.obtener_por_id(historial.id_historial)

        self.assertIsInstance(leido.fecha_registro, datetime)
        self.assertIs(leido.tipo_documento, TiposDocumento.LABORATORIO)

    def test_obtener_por_id_trae_el_uuid_que_genero_la_base(self):
        historial = self.repo.registrar(self.nuevo())

        leido = self.repo.obtener_por_id(historial.id_historial)

        self.assertIsNotNone(leido.uuid_publico)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_va_del_mas_reciente_al_mas_antiguo(self):
        self.repo.registrar(self.nuevo(fecha_registro="2026-01-15 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_registro="2026-03-20 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_registro="2026-02-10 09:00:00"))

        fechas = [h.fecha_registro for h in self.repo.obtener_todos()]

        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarHistorialMedico(HistorialMedicoTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        historial = self.nuevo()

        self.assertTrue(self.repo.guardar(historial))

        self.assertIsNotNone(historial.id_historial)
        self.assertEqual(self.contar("HistorialMedico"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        historial = self.repo.registrar(self.nuevo())

        historial.etiquetas = ["revisado"]
        self.assertTrue(self.repo.guardar(historial))

        self.assertEqual(self.contar("HistorialMedico"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(historial.id_historial).etiquetas, ["revisado"]
        )

    def test_no_pisa_el_uuid_publico_al_actualizar(self):
        """Lo omite del upsert cuando la entidad no lo trae."""
        historial = self.repo.registrar(self.nuevo())
        uuid_original = self.leer_fila(
            "HistorialMedico", id_historial=historial.id_historial
        )["uuid_publico"]

        historial.uuid_publico = None
        historial.etiquetas = ["nuevo"]
        self.assertTrue(self.repo.guardar(historial))

        self.assertEqual(
            self.leer_fila("HistorialMedico", id_historial=historial.id_historial)["uuid_publico"],
            uuid_original,
        )

    def test_el_json_sobrevive_una_vuelta_completa(self):
        anidado = {"signos": {"presion": "120/80"}, "notas": ["a", "b"]}
        historial = self.repo.registrar(self.nuevo(datos_dinamicos=anidado))

        self.assertEqual(
            self.repo.obtener_por_id(historial.id_historial).datos_dinamicos, anidado
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        historial = self.repo.registrar(self.nuevo())
        historial.documento_url = "ftp://malo"
        with self.assertRaises(ValueError):
            self.repo.guardar(historial)


class DarBajaHistorialMedico(HistorialMedicoTestCase):
    """Baja fisica: el registro del historial se borra."""

    def test_borra_la_fila(self):
        historial = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(historial))

        self.assertEqual(self.contar("HistorialMedico"), 0)

    def test_no_toca_al_paciente_ni_al_medico(self):
        historial = self.repo.registrar(self.nuevo())

        self.repo.darbaja(historial)

        self.assertEqual(self.contar("Paciente"), 1)
        self.assertEqual(self.contar("Medico"), 1)

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_historial=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
