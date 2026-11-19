"""Tabla Ingreso."""

from datetime import datetime

from .constants import Entidad


class Ingreso(Entidad):
    """Internamiento en una habitación, derivado de una cita.

    `id_cita` es NOT NULL UNIQUE: cada cita produce cuando mucho un ingreso.
    """

    _CAMPOS_CLAVE = ('id_ingreso',)

    def __init__(
        self,
        *,
        id_ingreso: int | None = None,
        fecha_ingreso: datetime | str,
        id_cita: int,
        num_habitacion: int,
        fecha_alta: datetime | str | None = None,
        id_recepcionista: int | None = None,
    ) -> None:
        self.id_ingreso = id_ingreso
        self.fecha_ingreso = fecha_ingreso
        self.fecha_alta = fecha_alta
        self.id_cita = id_cita
        self.num_habitacion = num_habitacion
        self.id_recepcionista = id_recepcionista

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Ingreso:
            self._validar_propiedades()

    @property
    def dado_de_alta(self) -> bool:
        return self.fecha_alta is not None

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_ingreso')
        self._validar_llave_foranea('id_cita')
        self._validar_llave_foranea('num_habitacion')
        self._validar_llave_foranea('id_recepcionista', opcional=True)

        self._validar_fecha_hora('fecha_ingreso')
        self._validar_fecha_hora('fecha_alta', opcional=True)

        if self.fecha_alta is not None and self.fecha_alta <= self.fecha_ingreso:
            self._fallar(
                'fecha_alta',
                self.fecha_alta,
                f"debe ser posterior a la fecha de ingreso ({self.fecha_ingreso})",
            )
