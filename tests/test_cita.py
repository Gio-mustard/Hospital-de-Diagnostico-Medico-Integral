"""Pruebas de CitaRepositorio y de su implementacion CitaSQLRepository.

Estan separadas en una clase por tema: el contrato de la interfaz, y luego un
grupo por cada operacion (registrar, obtener, guardar, darbaja). La idea es que
el nombre de la prueba que falla ya diga que se rompio sin tener que abrir el
archivo.
"""


import sqlite3
import unittest
from datetime import datetime

from model.cita import Cita
from model.constants import EstadosCita
from model.repositories import CitaRepositorio, CitaSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class CitaTestCase(RepositorioTestCase):
    """Añade a la base un repositorio de citas."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = CitaSQLRepository(self.db)

    def nueva_cita(self, **cambios) -> Cita:
        """Cita valida y sin persistir, apuntando a las FK ya creadas."""
        datos = {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
            "fecha_hora": "2026-12-01 10:30:00",
            "motivo": "Dolor abdominal",
        } | cambios
        return Cita(**datos)


# ======================================================================
# El contrato: la interfaz y quien la implementa
# ======================================================================


class ContratoDeCitaRepositorio(ContratoRepositorioMixin, CitaTestCase):
    """CitaRepositorio como interfaz, y CitaSQLRepository como implementacion."""

    interfaz = CitaRepositorio
    implementacion = CitaSQLRepository

    def test_un_doble_en_memoria_puede_sustituir_a_la_implementacion_sql(self):
        """Lo que justifica la interfaz: cambiar el almacenamiento sin tocar al consumidor."""

        class CitasEnMemoria(CitaRepositorio):
            def __init__(self):
                super().__init__(db=None)
                self.filas: dict[int, Cita] = {}

            def obtener_por_id(self, id_cita):
                return self.filas.get(id_cita)

            def obtener_todos(self):
                return tuple(self.filas.values())

            def registrar(self, entidad):
                entidad.id_cita = len(self.filas) + 1
                self.filas[entidad.id_cita] = entidad
                return entidad

            def guardar(self, entidad):
                self.filas[entidad.id_cita] = entidad
                return True

            def darbaja(self, entidad):
                entidad.estado = EstadosCita.CANCELADA
                return True

        doble = CitasEnMemoria()
        self.assertIsInstance(doble, CitaRepositorio)

        cita = doble.registrar(self.nueva_cita())
        self.assertEqual(cita.id_cita, 1)
        self.assertIs(doble.obtener_por_id(1), cita)


# ======================================================================
# registrar
# ======================================================================


class RegistrarCita(CitaTestCase):
    """registrar(entidad) inserta una cita nueva y le asigna su id."""

    def test_asigna_el_id_que_genero_la_base(self):
        cita = self.repo.registrar(self.nueva_cita())
        self.assertEqual(cita.id_cita, 1)

        segunda = self.repo.registrar(self.nueva_cita(motivo="Control"))
        self.assertEqual(segunda.id_cita, 2)

    def test_devuelve_la_misma_instancia_que_recibio(self):
        cita = self.nueva_cita()
        self.assertIs(self.repo.registrar(cita), cita)

    def test_deja_la_fila_escrita_con_sus_valores(self):
        cita = self.repo.registrar(
            self.nueva_cita(motivo="Dolor de cabeza", num_consultorio=None)
        )

        fila = self.leer_fila("Cita", id_cita=cita.id_cita)
        self.assertEqual(fila["id_paciente"], self.paciente.id_paciente)
        self.assertEqual(fila["id_medico"], self.medico.id_medico)
        self.assertEqual(fila["motivo"], "Dolor de cabeza")
        self.assertEqual(fila["estado"], "Programada")
        self.assertIsNone(fila["diagnostico"])

    def test_el_estado_por_defecto_es_programada(self):
        cita = self.repo.registrar(self.nueva_cita())
        self.assertIs(cita.estado, EstadosCita.PROGRAMADA)

    def test_guarda_la_fecha_con_el_formato_del_ddl(self):
        """El DDL exige TEXT 'YYYY-MM-DD HH:MM:SS' (chk_cita_fecha usa datetime())."""
        cita = self.repo.registrar(
            self.nueva_cita(fecha_hora=datetime(2026, 12, 1, 10, 30))
        )
        fila = self.leer_fila("Cita", id_cita=cita.id_cita)
        self.assertEqual(fila["fecha_hora"], "2026-12-01 10:30:00")

    def test_acepta_las_fk_opcionales(self):
        recep = self.crear_recepcionista()
        consultorio = self.crear_consultorio()

        cita = self.repo.registrar(
            self.nueva_cita(
                id_recepcionista=recep.id_recepcionista,
                num_consultorio=consultorio.num_consultorio,
            )
        )

        fila = self.leer_fila("Cita", id_cita=cita.id_cita)
        self.assertEqual(fila["id_recepcionista"], recep.id_recepcionista)
        self.assertEqual(fila["num_consultorio"], consultorio.num_consultorio)

    def test_valida_la_entidad_antes_de_escribir(self):
        """Una cita que se volvio invalida no debe llegar a la base."""
        cita = self.nueva_cita()
        cita.motivo = "   "  # el DDL lo acepta; la entidad no

        with self.assertRaises(ValueError):
            self.repo.registrar(cita)
        self.assertEqual(self.contar("Cita"), 0)

    def test_una_fk_inexistente_falla_en_la_base(self):
        cita = self.nueva_cita(id_paciente=9999)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(cita)


# ======================================================================
# obtener_por_id / obtener_todos
# ======================================================================


class ObtenerCitas(CitaTestCase):
    """Las lecturas reconstruyen la entidad con sus tipos de Python."""

    def test_obtener_por_id_reconstruye_la_cita(self):
        guardada = self.repo.registrar(self.nueva_cita(motivo="Revisión anual"))

        leida = self.repo.obtener_por_id(guardada.id_cita)

        self.assertIsInstance(leida, Cita)
        self.assertEqual(leida.id_cita, guardada.id_cita)
        self.assertEqual(leida.motivo, "Revisión anual")
        self.assertEqual(leida.id_paciente, self.paciente.id_paciente)

    def test_obtener_por_id_devuelve_los_tipos_del_dominio_no_texto(self):
        guardada = self.repo.registrar(self.nueva_cita())

        leida = self.repo.obtener_por_id(guardada.id_cita)

        self.assertIsInstance(leida.fecha_hora, datetime)
        self.assertEqual(leida.fecha_hora, datetime(2026, 12, 1, 10, 30))
        self.assertIs(leida.estado, EstadosCita.PROGRAMADA)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_va_de_la_mas_reciente_a_la_mas_antigua(self):
        self.repo.registrar(self.nueva_cita(fecha_hora="2026-01-15 09:00:00"))
        self.repo.registrar(self.nueva_cita(fecha_hora="2026-03-20 09:00:00"))
        self.repo.registrar(self.nueva_cita(fecha_hora="2026-02-10 09:00:00"))

        fechas = [c.fecha_hora for c in self.repo.obtener_todos()]

        self.assertEqual(fechas, sorted(fechas, reverse=True))
        self.assertEqual(fechas[0], datetime(2026, 3, 20, 9, 0))

    def test_obtener_todos_devuelve_una_tupla_de_citas(self):
        self.repo.registrar(self.nueva_cita())
        todas = self.repo.obtener_todos()

        self.assertIsInstance(todas, tuple)
        self.assertEqual(len(todas), 1)
        self.assertIsInstance(todas[0], Cita)


# ======================================================================
# guardar (upsert)
# ======================================================================


class GuardarCita(CitaTestCase):
    """guardar(entidad) inserta si no hay llave, y actualiza si ya la hay."""

    def test_sin_id_inserta_y_asigna_el_id(self):
        cita = self.nueva_cita()
        self.assertIsNone(cita.id_cita)

        self.assertTrue(self.repo.guardar(cita))

        self.assertIsNotNone(cita.id_cita)
        self.assertEqual(self.contar("Cita"), 1)

    def test_con_id_actualiza_la_fila_sin_duplicarla(self):
        cita = self.repo.registrar(self.nueva_cita(motivo="Motivo inicial"))

        cita.motivo = "Motivo corregido"
        self.assertTrue(self.repo.guardar(cita))

        self.assertEqual(self.contar("Cita"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(cita.id_cita).motivo, "Motivo corregido"
        )

    def test_puede_completar_una_cita_con_su_diagnostico(self):
        cita = self.repo.registrar(self.nueva_cita())

        cita.estado = EstadosCita.COMPLETADA
        cita.diagnostico = "Gastritis leve"
        self.assertTrue(self.repo.guardar(cita))

        leida = self.repo.obtener_por_id(cita.id_cita)
        self.assertIs(leida.estado, EstadosCita.COMPLETADA)
        self.assertEqual(leida.diagnostico, "Gastritis leve")

    def test_valida_la_entidad_antes_de_escribir(self):
        """La regla 'Completada exige diagnostico' vive en la entidad y en el DDL."""
        cita = self.repo.registrar(self.nueva_cita())
        cita.estado = EstadosCita.COMPLETADA  # sin diagnostico

        with self.assertRaises(ValueError):
            self.repo.guardar(cita)

        # La fila sigue como estaba
        self.assertEqual(
            self.leer_fila("Cita", id_cita=cita.id_cita)["estado"], "Programada"
        )


# ======================================================================
# darbaja
# ======================================================================


class DarBajaCita(CitaTestCase):
    """Para una cita, darse de baja es cancelarse: baja logica, no DELETE."""

    def test_cancela_la_cita_en_la_base(self):
        cita = self.repo.registrar(self.nueva_cita())

        self.assertTrue(self.repo.darbaja(cita))

        fila = self.leer_fila("Cita", id_cita=cita.id_cita)
        self.assertEqual(fila["estado"], "Cancelada")

    def test_no_borra_la_fila(self):
        cita = self.repo.registrar(self.nueva_cita())
        self.repo.darbaja(cita)
        self.assertEqual(self.contar("Cita"), 1)

    def test_refleja_la_cancelacion_en_la_entidad_recibida(self):
        cita = self.repo.registrar(self.nueva_cita())

        self.repo.darbaja(cita)

        self.assertIs(cita.estado, EstadosCita.CANCELADA)

    def test_sin_id_devuelve_false_y_no_toca_la_base(self):
        cita = self.nueva_cita()  # nunca se persistio

        self.assertFalse(self.repo.darbaja(cita))
        self.assertEqual(self.contar("Cita"), 0)

    def test_con_id_inexistente_devuelve_false(self):
        cita = self.nueva_cita(id_cita=9999)
        self.assertFalse(self.repo.darbaja(cita))

    def _cita_completada(self) -> Cita:
        return self.repo.registrar(
            self.nueva_cita(estado=EstadosCita.COMPLETADA, diagnostico="Gastritis")
        )

    def test_no_se_permite_cancelar_una_cita_ya_completada(self):
        """La atencion ya ocurrio: su diagnostico es parte del expediente."""
        cita = self._cita_completada()

        with self.assertRaises(ValueError):
            self.repo.darbaja(cita)

    def test_al_rechazar_la_cancelacion_no_toca_la_fila(self):
        cita = self._cita_completada()

        with self.assertRaises(ValueError):
            self.repo.darbaja(cita)

        fila = self.leer_fila("Cita", id_cita=cita.id_cita)
        self.assertEqual(fila["estado"], "Completada")
        self.assertEqual(fila["diagnostico"], "Gastritis")
        self.assertIs(cita.estado, EstadosCita.COMPLETADA)

    def test_decide_por_el_estado_de_la_base_no_por_la_entidad(self):
        """La entidad en memoria puede venir desactualizada; la base manda."""
        cita = self._cita_completada()

        # Alguien trae una copia vieja, de cuando la cita estaba Programada.
        copia = self.repo.obtener_por_id(cita.id_cita)
        copia.estado = EstadosCita.PROGRAMADA
        copia.diagnostico = None

        with self.assertRaises(ValueError):
            self.repo.darbaja(copia)

    def test_cancelar_una_cita_no_asistida_si_se_permite(self):
        """Solo 'Completada' bloquea la cancelacion, no cualquier estado previo."""
        cita = self.repo.registrar(self.nueva_cita(estado=EstadosCita.NO_ASISTIO))

        self.assertTrue(self.repo.darbaja(cita))
        self.assertEqual(
            self.leer_fila("Cita", id_cita=cita.id_cita)["estado"], "Cancelada"
        )

    def test_cancelar_dos_veces_es_inofensivo(self):
        cita = self.repo.registrar(self.nueva_cita())

        self.assertTrue(self.repo.darbaja(cita))
        self.assertTrue(self.repo.darbaja(cita))
        self.assertIs(cita.estado, EstadosCita.CANCELADA)


if __name__ == "__main__":
    unittest.main(verbosity=2)
