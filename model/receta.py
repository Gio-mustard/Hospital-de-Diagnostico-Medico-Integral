"""Tabla Receta."""

from datetime import date

from .constants import CLAVES_TRATAMIENTO, Entidad


class Receta(Entidad):
    """Prescripción que nace de una cita o de un ingreso de emergencia.

    `tratamiento` es el JSONB del DDL y debe traer las tres llaves de
    `CLAVES_TRATAMIENTO`.
    """

    _CAMPOS_CLAVE = ('id_receta',)

    def __init__(
        self,
        *,
        id_receta: int | None = None,
        fecha_emision: date | str,
        tratamiento: dict | str,
        id_cita: int | None = None,
        id_ingreso_emergencia: int | None = None,
    ) -> None:
        self.id_receta = id_receta
        self.id_cita = id_cita
        self.id_ingreso_emergencia = id_ingreso_emergencia
        self.fecha_emision = fecha_emision
        self.tratamiento = tratamiento

    @property
    def por_emergencia(self) -> bool:
        return self.id_ingreso_emergencia is not None

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_receta')
        self._validar_llave_foranea('id_cita', opcional=True)
        self._validar_llave_foranea('id_ingreso_emergencia', opcional=True)

        # chk_receta_fecha
        self._validar_fecha('fecha_emision')

        # chk_receta_json_estructura
        self._validar_json('tratamiento', dict, claves=CLAVES_TRATAMIENTO)

        # chk_receta_xor_origen: exactamente uno de los dos orígenes
        origenes = (self.id_cita is not None) + (self.id_ingreso_emergencia is not None)
        if origenes != 1:
            self._fallar(
                'id_cita',
                self.id_cita,
                "la receta debe venir de una cita o de un ingreso de emergencia, "
                f"nunca de los dos ni de ninguno (recibió {origenes})",
            )
