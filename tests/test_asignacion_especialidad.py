"""Pruebas de AsignacionEspecialidadRepositorio.

Caso raro: un solo repositorio sirve a DOS tablas con la misma forma,
MedicoEspecialidad y EnfermeroEspecialidad, que se diferencian solo en como se
llama la columna del titular (`id_medico` o `id_enfermero`). Las dos tienen PK
compuesta con `id_esp`.
"""

import inspect
import sqlite3
import unittest

from model.asignacion_especialidad import (
    AsignacionEspecialidad,
    EnfermeroEspecialidad,
    MedicoEspecialidad,
)
from model.repositories import (
    AsignacionEspecialidadRepositorio,
    AsignacionEspecialidadSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase

DOCUMENTOS = "https://documentos.hospital.com/cedula-cardio.pdf"


class AsignacionTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = AsignacionEspecialidadSQLRepository(self.db)

    def nueva_de_medico(self, **cambios) -> MedicoEspecialidad:
        datos = {
            "id_medico": self.medico.id_medico,
            "id_esp": self.especialidad.id_esp,
        } | cambios
        return MedicoEspecialidad(**datos)

    def nueva_de_enfermero(self, **cambios) -> EnfermeroEspecialidad:
        datos = {
            "id_enfermero": self.enfermero.id_enfermero,
            "id_esp": self.especialidad.id_esp,
        } | cambios
        return EnfermeroEspecialidad(**datos)


class ContratoDeAsignacion(ContratoRepositorioMixin, AsignacionTestCase):
    """AsignacionEspecialidadRepositorio y su implementacion SQL."""

    interfaz = AsignacionEspecialidadRepositorio
    implementacion = AsignacionEspecialidadSQLRepository

    def test_obtener_por_id_pide_la_llave_compuesta_y_la_bandera(self):
        argumentos = list(
            inspect.signature(AsignacionEspecialidadRepositorio.obtener_por_id).parameters
        )
        self.assertEqual(argumentos, ["self", "id_titular", "id_esp", "es_enfermero"])


class DespachoPorTipo(AsignacionTestCase):
    """El tipo de la entidad decide a que tabla va."""

    def test_una_asignacion_de_medico_va_a_MedicoEspecialidad(self):
        tabla, columna, clase = self.repo._destino(self.nueva_de_medico())

        self.assertEqual(tabla, "MedicoEspecialidad")
        self.assertEqual(columna, "id_medico")
        self.assertIs(clase, MedicoEspecialidad)

    def test_una_asignacion_de_enfermero_va_a_EnfermeroEspecialidad(self):
        tabla, columna, clase = self.repo._destino(self.nueva_de_enfermero())

        self.assertEqual(tabla, "EnfermeroEspecialidad")
        self.assertEqual(columna, "id_enfermero")
        self.assertIs(clase, EnfermeroEspecialidad)

    def test_otra_cosa_es_un_error_de_tipo(self):
        with self.assertRaises(TypeError):
            self.repo._destino(self.medico)

    def test_el_titular_se_lee_por_la_propiedad_comun(self):
        """`id_titular` abstrae id_medico / id_enfermero."""
        self.assertEqual(self.nueva_de_medico().id_titular, self.medico.id_medico)
        self.assertEqual(
            self.nueva_de_enfermero().id_titular, self.enfermero.id_enfermero
        )


class RegistrarAsignacion(AsignacionTestCase):
    def test_escribe_en_la_tabla_del_medico(self):
        asignacion = self.repo.registrar(self.nueva_de_medico(institucion="UABC"))

        fila = self.leer_fila(
            "MedicoEspecialidad",
            id_medico=asignacion.id_medico,
            id_esp=asignacion.id_esp,
        )
        self.assertEqual(fila["institucion"], "UABC")
        self.assertEqual(self.contar("EnfermeroEspecialidad"), 0)

    def test_escribe_en_la_tabla_del_enfermero(self):
        asignacion = self.repo.registrar(self.nueva_de_enfermero())

        self.assertIsNotNone(
            self.leer_fila(
                "EnfermeroEspecialidad",
                id_enfermero=asignacion.id_enfermero,
                id_esp=asignacion.id_esp,
            )
        )
        self.assertEqual(self.contar("MedicoEspecialidad"), 0)

    def test_devuelve_la_misma_instancia(self):
        asignacion = self.nueva_de_medico()
        self.assertIs(self.repo.registrar(asignacion), asignacion)

    def test_los_documentos_y_la_institucion_son_opcionales(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())

        fila = self.leer_fila(
            "MedicoEspecialidad", id_medico=asignacion.id_medico, id_esp=asignacion.id_esp
        )
        self.assertIsNone(fila["documentos"])
        self.assertIsNone(fila["institucion"])

    def test_la_misma_llave_compuesta_no_se_puede_repetir(self):
        self.repo.registrar(self.nueva_de_medico())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nueva_de_medico())

    def test_un_medico_puede_tener_varias_especialidades(self):
        otra = self.crear_especialidad()

        self.repo.registrar(self.nueva_de_medico())
        self.repo.registrar(self.nueva_de_medico(id_esp=otra.id_esp))

        self.assertEqual(self.contar("MedicoEspecialidad"), 2)

    def test_un_medico_y_un_enfermero_pueden_compartir_especialidad(self):
        """Son tablas distintas: no hay conflicto de llaves."""
        self.repo.registrar(self.nueva_de_medico())
        self.repo.registrar(self.nueva_de_enfermero())

        self.assertEqual(self.contar("MedicoEspecialidad"), 1)
        self.assertEqual(self.contar("EnfermeroEspecialidad"), 1)

    def test_los_documentos_tienen_que_ser_https(self):
        with self.assertRaises(ValueError):
            self.nueva_de_medico(documentos="http://insegura.com/x.pdf")

    def test_una_fk_inexistente_falla_en_la_base(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nueva_de_medico(id_esp=9999))

    def test_valida_la_entidad_antes_de_escribir(self):
        asignacion = self.nueva_de_medico()
        asignacion.documentos = "no-es-url"
        with self.assertRaises(ValueError):
            self.repo.registrar(asignacion)
        self.assertEqual(self.contar("MedicoEspecialidad"), 0)


class ObtenerAsignaciones(AsignacionTestCase):
    """La bandera `es_enfermero` elige la tabla que se consulta."""

    def test_obtener_por_id_lee_la_tabla_del_medico_por_defecto(self):
        asignacion = self.repo.registrar(self.nueva_de_medico(documentos=DOCUMENTOS))

        leida = self.repo.obtener_por_id(asignacion.id_medico, asignacion.id_esp)

        self.assertIsInstance(leida, MedicoEspecialidad)
        self.assertEqual(leida.documentos, DOCUMENTOS)

    def test_obtener_por_id_con_la_bandera_lee_la_del_enfermero(self):
        asignacion = self.repo.registrar(self.nueva_de_enfermero())

        leida = self.repo.obtener_por_id(
            asignacion.id_enfermero, asignacion.id_esp, es_enfermero=True
        )

        self.assertIsInstance(leida, EnfermeroEspecialidad)

    def test_la_bandera_equivocada_no_encuentra_nada(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())

        self.assertIsNone(
            self.repo.obtener_por_id(
                asignacion.id_medico, asignacion.id_esp, es_enfermero=True
            )
        )

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999, 9999))

    def test_obtener_todos_junta_las_dos_tablas_medicos_primero(self):
        self.repo.registrar(self.nueva_de_enfermero())
        self.repo.registrar(self.nueva_de_medico())

        todas = self.repo.obtener_todos()

        self.assertEqual(len(todas), 2)
        self.assertTrue(all(isinstance(a, AsignacionEspecialidad) for a in todas))
        self.assertEqual(
            [type(a).__name__ for a in todas],
            ["MedicoEspecialidad", "EnfermeroEspecialidad"],
        )

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarAsignacion(AsignacionTestCase):
    def test_inserta_cuando_la_llave_es_nueva(self):
        self.assertTrue(self.repo.guardar(self.nueva_de_medico()))
        self.assertEqual(self.contar("MedicoEspecialidad"), 1)

    def test_actualiza_cuando_la_llave_ya_existe(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())

        asignacion.institucion = "UNAM"
        self.assertTrue(self.repo.guardar(asignacion))

        self.assertEqual(self.contar("MedicoEspecialidad"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(
                asignacion.id_medico, asignacion.id_esp
            ).institucion,
            "UNAM",
        )

    def test_guarda_en_la_tabla_del_enfermero_cuando_toca(self):
        asignacion = self.repo.registrar(self.nueva_de_enfermero())

        asignacion.institucion = "IPN"
        self.assertTrue(self.repo.guardar(asignacion))

        self.assertEqual(
            self.leer_fila(
                "EnfermeroEspecialidad",
                id_enfermero=asignacion.id_enfermero,
                id_esp=asignacion.id_esp,
            )["institucion"],
            "IPN",
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())
        asignacion.documentos = "ftp://malo"
        with self.assertRaises(ValueError):
            self.repo.guardar(asignacion)


class DarBajaAsignacion(AsignacionTestCase):
    """Baja fisica, en la tabla que corresponda."""

    def test_borra_la_asignacion_del_medico(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())

        self.assertTrue(self.repo.darbaja(asignacion))

        self.assertEqual(self.contar("MedicoEspecialidad"), 0)

    def test_borra_solo_en_su_tabla(self):
        self.repo.registrar(self.nueva_de_enfermero())
        del_medico = self.repo.registrar(self.nueva_de_medico())

        self.assertTrue(self.repo.darbaja(del_medico))

        self.assertEqual(self.contar("MedicoEspecialidad"), 0)
        self.assertEqual(self.contar("EnfermeroEspecialidad"), 1)

    def test_no_borra_al_titular_ni_la_especialidad(self):
        asignacion = self.repo.registrar(self.nueva_de_medico())

        self.repo.darbaja(asignacion)

        self.assertEqual(self.contar("Medico"), 1)
        self.assertEqual(self.contar("Especialidad"), 1)

    def test_con_una_llave_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva_de_medico(id_esp=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
