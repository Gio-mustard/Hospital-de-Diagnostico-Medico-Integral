"""Pruebas de Entidad: identidad de las entidades y normalizacion de fechas.

No tocan la base de datos. Lo que se prueba es la raiz del dominio: cuando dos
entidades son la misma, cuando se pueden meter en un conjunto, y como se
normaliza un TIMESTAMP antes de que llegue al DDL.
"""

import unittest
from datetime import date, datetime

from model.cita import Cita
from model.detalle_receta import DetalleReceta
from model.especialidad import Especialidad
from model.habitacion import Habitacion


def cita(**cambios) -> Cita:
    datos = {
        "id_paciente": 1,
        "id_medico": 1,
        "fecha_hora": "2026-12-01 10:30:00",
        "motivo": "Consulta",
    } | cambios
    return Cita(**datos)


class LlaveDeLaEntidad(unittest.TestCase):
    """`clave` es la llave de la clase mas derivada, la que de verdad identifica."""

    def test_una_entidad_sin_insertar_no_tiene_llave(self):
        self.assertIsNone(cita().clave)

    def test_una_entidad_insertada_expone_su_llave(self):
        self.assertEqual(cita(id_cita=7).clave, 7)

    def test_la_llave_compuesta_es_una_tupla(self):
        detalle = DetalleReceta(id_receta=3, id_medicamento=9, dosis_indicaciones="1 c/8h")
        self.assertEqual(detalle.clave, (3, 9))

    def test_una_llave_compuesta_incompleta_no_cuenta_como_llave(self):
        """Con media llave la entidad no esta identificada."""
        detalle = DetalleReceta(id_receta=3, id_medicamento=9, dosis_indicaciones="1 c/8h")
        detalle.id_medicamento = None

        self.assertIsNone(detalle.clave)

    def test_una_pk_manual_tiene_llave_desde_que_se_construye(self):
        """Habitacion no usa AUTOINCREMENT: el numero lo pone quien la crea."""
        hab = Habitacion(num_habitacion=101, piso=1, tipo="Individual", estado="Disponible")
        self.assertEqual(hab.clave, 101)


class IgualdadDeEntidades(unittest.TestCase):
    """Dos entidades son la misma si son del mismo tipo y comparten llave."""

    def test_misma_llave_es_la_misma_entidad(self):
        self.assertEqual(cita(id_cita=1), cita(id_cita=1, motivo="Otro motivo"))

    def test_llaves_distintas_son_entidades_distintas(self):
        self.assertNotEqual(cita(id_cita=1), cita(id_cita=2))

    def test_tipos_distintos_nunca_son_iguales(self):
        esp = Especialidad(id_esp=1, nombre="Cardiología")
        self.assertNotEqual(cita(id_cita=1), esp)

    def test_sin_llave_cada_objeto_solo_es_igual_a_si_mismo(self):
        una = cita()
        otra = cita()

        self.assertEqual(una, una)
        self.assertNotEqual(una, otra)

    def test_una_sin_llave_no_es_igual_a_una_con_llave(self):
        self.assertNotEqual(cita(), cita(id_cita=1))

    def test_dos_llaves_compuestas_incompletas_no_se_confunden(self):
        """Antes (None, None) == (None, None) las hacia pasar por la misma."""
        una = DetalleReceta(id_receta=1, id_medicamento=1, dosis_indicaciones="x")
        otra = DetalleReceta(id_receta=1, id_medicamento=1, dosis_indicaciones="x")
        una.id_receta = una.id_medicamento = None
        otra.id_receta = otra.id_medicamento = None

        self.assertNotEqual(una, otra)


class HashDeEntidades(unittest.TestCase):
    """El hash sale de la llave, y sin llave la entidad no es hasheable."""

    def test_entidades_iguales_tienen_el_mismo_hash(self):
        self.assertEqual(hash(cita(id_cita=1)), hash(cita(id_cita=1)))

    def test_el_hash_distingue_el_tipo(self):
        """Dos entidades con el id 1 no deberian colisionar por ser de tablas distintas."""
        esp = Especialidad(id_esp=1, nombre="Cardiología")
        self.assertNotEqual(hash(cita(id_cita=1)), hash(esp))

    def test_una_entidad_insertada_sirve_de_llave_en_un_dict(self):
        agenda = {cita(id_cita=1): "consultorio 5"}

        self.assertEqual(agenda[cita(id_cita=1)], "consultorio 5")

    def test_una_entidad_sin_llave_no_se_puede_hashear(self):
        """Avisa al meterla, en vez de desaparecer del set cuando se persista."""
        with self.assertRaises(TypeError) as capturado:
            {cita()}

        self.assertIn("llave primaria", str(capturado.exception))

    def test_el_hash_no_cambia_a_media_vida_del_objeto(self):
        """Una vez con llave, el hash es estable aunque cambien otros campos."""
        una = cita(id_cita=1)
        antes = hash(una)

        una.motivo = "Motivo corregido"
        una.diagnostico = None

        self.assertEqual(hash(una), antes)
        self.assertIn(una, {una})


class NormalizacionDeFechaHora(unittest.TestCase):
    """Los validadores dejan el valor listo para el formato del DDL."""

    def test_descarta_los_microsegundos(self):
        """El DDL guarda segundos: `datetime.now()` entraba y reventaba al insertar."""
        c = cita(fecha_hora=datetime(2026, 12, 1, 10, 30, 59, 32280))

        self.assertEqual(c.fecha_hora, datetime(2026, 12, 1, 10, 30, 59))
        self.assertEqual(c.fecha_hora.microsecond, 0)

    def test_descarta_los_microsegundos_de_datetime_now(self):
        c = cita(fecha_hora=datetime.now())

        self.assertEqual(c.fecha_hora.microsecond, 0)

    def test_el_texto_se_vuelve_datetime(self):
        c = cita(fecha_hora="2026-12-01 10:30:00")

        self.assertIsInstance(c.fecha_hora, datetime)
        self.assertEqual(c.fecha_hora, datetime(2026, 12, 1, 10, 30))

    def test_el_texto_con_microsegundos_tambien_se_trunca(self):
        c = cita(fecha_hora="2026-12-01 10:30:59.032280")

        self.assertEqual(c.fecha_hora, datetime(2026, 12, 1, 10, 30, 59))

    def test_lo_que_no_es_fecha_se_rechaza(self):
        with self.assertRaises(ValueError):
            cita(fecha_hora="mañana por la tarde")

    def test_al_serializar_queda_el_formato_del_ddl(self):
        """19 caracteres: 'YYYY-MM-DD HH:MM:SS', lo que exige el CHECK."""
        c = cita(fecha_hora=datetime.now())

        self.assertEqual(len(c.fecha_hora.isoformat(sep=" ")), 19)


class NormalizacionDeFecha(unittest.TestCase):
    """DATE del DDL: 'YYYY-MM-DD', sin hora."""

    @staticmethod
    def _receta(fecha_emision):
        from model.receta import Receta

        return Receta(
            id_cita=1,
            fecha_emision=fecha_emision,
            tratamiento={
                "diagnostico": "X",
                "medicamentos": [],
                "indicaciones_generales": "Y",
            },
        )

    def test_el_texto_se_vuelve_date(self):
        receta = self._receta("2026-12-01")

        self.assertIsInstance(receta.fecha_emision, date)
        self.assertNotIsInstance(receta.fecha_emision, datetime)
        self.assertEqual(receta.fecha_emision, date(2026, 12, 1))

    def test_un_datetime_se_recorta_a_date(self):
        receta = self._receta(datetime(2026, 12, 1, 10, 30))

        self.assertIsInstance(receta.fecha_emision, date)
        self.assertEqual(receta.fecha_emision, date(2026, 12, 1))

    def test_lo_que_no_es_fecha_se_rechaza(self):
        with self.assertRaises(ValueError):
            self._receta("01/12/2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
