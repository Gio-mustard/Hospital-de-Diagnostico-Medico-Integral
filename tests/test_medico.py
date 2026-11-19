"""Pruebas de MedicoRepositorio.

Un medico vive en tres tablas: DerechoHabiente -> Trabajador -> Medico. Este
repositorio se apoya en el de Trabajador (que a su vez se apoya en el de
DerechoHabiente), asi que lo que se prueba es que la cascada quede completa y
que el JOIN de tres vias rearme la entidad.
"""

import sqlite3
import unittest

from model.medico import Medico
from model.repositories import MedicoRepositorio, MedicoSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class MedicoTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = MedicoSQLRepository(self.db)

    def nuevo(self, **cambios) -> Medico:
        n = self._siguiente()
        datos = (
            self._datos_persona(n, "H")
            | self._datos_trabajador(n)
            | {"cedula_profesional": f"{1000000 + n}"}
            | cambios
        )
        return Medico(**datos)


class ContratoDeMedico(ContratoRepositorioMixin, MedicoTestCase):
    """MedicoRepositorio y su implementacion SQL."""

    interfaz = MedicoRepositorio
    implementacion = MedicoSQLRepository

    def test_el_colaborador_comparte_la_misma_base(self):
        self.assertIs(self.repo._trab_repo.db, self.db)


class RegistrarMedico(MedicoTestCase):
    """registrar(entidad) tiene que dejar las tres filas."""

    def test_escribe_en_las_tres_tablas(self):
        self.repo.registrar(self.nuevo())

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("Medico"), 1)

    def test_asigna_los_tres_ids(self):
        med = self.repo.registrar(self.nuevo())

        self.assertEqual(med.id_derechohabiente, 1)
        self.assertEqual(med.id_trabajador, 1)
        self.assertEqual(med.id_medico, 1)

    def test_la_fila_de_medico_apunta_a_su_trabajador(self):
        med = self.repo.registrar(self.nuevo(cedula_profesional="9876543"))

        fila = self.leer_fila("Medico", id_medico=med.id_medico)
        self.assertEqual(fila["id_trabajador"], med.id_trabajador)
        self.assertEqual(fila["cedula_profesional"], "9876543")
        self.assertEqual(fila["activo"], 1)

    def test_reutiliza_el_trabajador_si_ya_tiene_id(self):
        trab = self.crear_trabajador()

        med = self.repo.registrar(
            self.nuevo(
                id_trabajador=trab.id_trabajador,
                id_derechohabiente=trab.id_derechohabiente,
                curp=trab.curp,
                telefono=trab.telefono,
                numero_empleado=trab.numero_empleado,
            )
        )

        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(med.id_trabajador, trab.id_trabajador)

    def test_la_cedula_repetida_choca_con_el_unique(self):
        primero = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(cedula_profesional=primero.cedula_profesional))

    def test_valida_la_entidad_antes_de_escribir(self):
        med = self.nuevo()
        med.cedula_profesional = "ABC"  # el DDL exige 7 a 10 digitos
        with self.assertRaises(ValueError):
            self.repo.registrar(med)
        self.assertEqual(self.contar("Medico"), 0)
        self.assertEqual(self.contar("DerechoHabiente"), 0)


class ObtenerMedicos(MedicoTestCase):
    """Leer un medico exige el JOIN de las tres tablas."""

    def test_obtener_por_id_trae_los_datos_de_las_tres_tablas(self):
        med = self.repo.registrar(
            self.nuevo(nombres="Ricardo", departamento="Cardiología")
        )

        leido = self.repo.obtener_por_id(med.id_medico)

        self.assertIsInstance(leido, Medico)
        self.assertEqual(leido.nombres, "Ricardo")  # DerechoHabiente
        self.assertEqual(leido.departamento, "Cardiología")  # Trabajador
        self.assertEqual(leido.cedula_profesional, med.cedula_profesional)  # Medico
        self.assertIsInstance(leido.activo, bool)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_un_trabajador_que_no_es_medico_no_aparece(self):
        self.crear_trabajador()
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_apellidos_y_nombre(self):
        self.repo.registrar(self.nuevo(apellido_paterno="Zamora", apellido_materno="A"))
        self.repo.registrar(self.nuevo(apellido_paterno="Alvarez", apellido_materno="B"))

        apellidos = [m.apellido_paterno for m in self.repo.obtener_todos()]

        self.assertEqual(apellidos, ["Alvarez", "Zamora"])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarMedico(MedicoTestCase):
    def test_sin_ids_inserta_en_las_tres_tablas(self):
        med = self.nuevo()

        self.assertTrue(self.repo.guardar(med))

        self.assertEqual(self.contar("DerechoHabiente"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("Medico"), 1)

    def test_actualiza_columnas_de_los_tres_niveles(self):
        med = self.repo.registrar(self.nuevo())

        med.ciudad = "Tijuana"  # DerechoHabiente
        med.departamento = "Neurología"  # Trabajador
        med.cedula_profesional = "7654321"  # Medico
        self.assertTrue(self.repo.guardar(med))

        leido = self.repo.obtener_por_id(med.id_medico)
        self.assertEqual(leido.ciudad, "Tijuana")
        self.assertEqual(leido.departamento, "Neurología")
        self.assertEqual(leido.cedula_profesional, "7654321")

    def test_no_duplica_filas(self):
        med = self.repo.registrar(self.nuevo())

        self.repo.guardar(med)
        self.repo.guardar(med)

        self.assertEqual(self.contar("Medico"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)

    def test_valida_la_entidad_antes_de_escribir(self):
        med = self.repo.registrar(self.nuevo())
        med.cedula_profesional = "1"
        with self.assertRaises(ValueError):
            self.repo.guardar(med)


class DarBajaMedico(MedicoTestCase):
    """Baja logica en los tres niveles."""

    def test_da_de_baja_en_las_tres_tablas(self):
        med = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(med))

        self.assertEqual(
            self.leer_fila("DerechoHabiente", id_derechohabiente=med.id_derechohabiente)["activo"],
            0,
        )
        self.assertEqual(
            self.leer_fila("Trabajador", id_trabajador=med.id_trabajador)["activo"], 0
        )
        self.assertEqual(self.leer_fila("Medico", id_medico=med.id_medico)["activo"], 0)

    def test_no_borra_ninguna_fila(self):
        med = self.repo.registrar(self.nuevo())

        self.repo.darbaja(med)

        self.assertEqual(self.contar("Medico"), 1)
        self.assertEqual(self.contar("Trabajador"), 1)
        self.assertEqual(self.contar("DerechoHabiente"), 1)

    def test_completa_los_ids_que_la_entidad_no_trae(self):
        """Con solo el id_medico, el repositorio busca el resto de la cadena."""
        med = self.repo.registrar(self.nuevo())

        suelto = self.nuevo(
            id_medico=med.id_medico, id_trabajador=None, id_derechohabiente=None
        )
        self.assertTrue(self.repo.darbaja(suelto))

        self.assertEqual(suelto.id_trabajador, med.id_trabajador)
        self.assertEqual(suelto.id_derechohabiente, med.id_derechohabiente)

    def test_sin_ningun_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_medico=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
