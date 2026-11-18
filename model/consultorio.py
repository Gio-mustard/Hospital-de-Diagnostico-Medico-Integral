"""Tabla Consultorio."""

from .constants import EstadosConsultorio
from .espacio_fisico import EspacioFisico


class Consultorio (EspacioFisico) :
    """Consultorio de consulta externa. PK manual `num_consultorio`."""

    _CAMPOS_CLAVE = ('numero',)
    _ESTADOS = EstadosConsultorio

    def __init__(
        self,
        *,
        num_consultorio: int,
        piso: int,
        departamento: str,
        estado: EstadosConsultorio | str,
    ) -> None:
        super().__init__(numero=num_consultorio, piso=piso, estado=estado)
        self.departamento = departamento

    @property
    def num_consultorio(self) -> int:
        """Alias con el nombre que lleva la columna en el DDL."""
        return self.numero

    @property
    def disponible(self) -> bool:
        return self.estado is EstadosConsultorio.DISPONIBLE

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()

        self._validar_texto('departamento', 100)
