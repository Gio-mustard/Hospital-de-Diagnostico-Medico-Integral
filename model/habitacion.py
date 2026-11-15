"""Tabla Habitacion."""

from .constants import EstadosHabitacion, TiposHabitacion
from .espacio_fisico import EspacioFisico


class Habitacion(EspacioFisico):
    """Habitación de internamiento. PK manual `num_habitacion`."""

    _CAMPOS_CLAVE = ('numero',)
    _ESTADOS = EstadosHabitacion

    def __init__(
        self,
        *,
        num_habitacion: int,
        piso: int,
        tipo: TiposHabitacion | str,
        estado: EstadosHabitacion | str,
    ) -> None:
        super().__init__(numero=num_habitacion, piso=piso, estado=estado)
        self.tipo = tipo

    @property
    def num_habitacion(self) -> int:
        """Alias con el nombre que lleva la columna en el DDL."""
        return self.numero

    @property
    def disponible(self) -> bool:
        return self.estado is EstadosHabitacion.DISPONIBLE

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()

        # chk_hab_tipo
        self._validar_enum('tipo', TiposHabitacion)
