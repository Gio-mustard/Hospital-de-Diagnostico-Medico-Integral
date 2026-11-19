"""Clase abstracta compartida por Habitacion y Consultorio.

Las dos tablas del DDL tienen la misma forma: una llave primaria numérica
capturada a mano (sin AUTOINCREMENT), un `piso BETWEEN 1 AND 20` y un `estado`
tomado de un catálogo. Lo único que cambia es el catálogo de estados y las
columnas propias de cada una, así que la parte común se escribe aquí.
"""

from abc import abstractmethod
from enum import Enum
from typing import ClassVar

from .constants import PISO_MAXIMO, PISO_MINIMO, Entidad


class EspacioFisico(Entidad):
    """Espacio del hospital identificado por un número de piso y un estado.

    Es abstracta: quien hereda define su catálogo de estados (`_ESTADOS`) y qué
    significa que el espacio se pueda asignar (`disponible`).
    """

    _ESTADOS: ClassVar[type[Enum]]

    def __init__(self, *, numero: int, piso: int, estado: Enum | str) -> None:
        self.numero = numero
        self.piso = piso
        self.estado = estado

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is EspacioFisico:
            self._validar_propiedades()

    @property
    @abstractmethod
    def disponible(self) -> bool:
        """¿El espacio se puede asignar en este momento?"""

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()

        self._validar_entero('numero', minimo=1)

        self._validar_entero('piso', minimo=PISO_MINIMO, maximo=PISO_MAXIMO)

        self._validar_enum('estado', self._ESTADOS)
