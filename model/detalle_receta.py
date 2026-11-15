"""Tabla DetalleReceta."""

from .constants import Entidad


class DetalleReceta(Entidad):
    """Renglón de una receta: qué medicamento y con qué indicaciones.

    PK compuesta (id_receta, id_medicamento), así que un medicamento no se
    puede repetir dentro de la misma receta.
    """

    _CAMPOS_CLAVE = ('id_receta', 'id_medicamento')

    def __init__(
        self,
        *,
        id_receta: int,
        id_medicamento: int,
        dosis_indicaciones: str,
    ) -> None:
        self.id_receta = id_receta
        self.id_medicamento = id_medicamento
        self.dosis_indicaciones = dosis_indicaciones

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_llave_foranea('id_receta')
        self._validar_llave_foranea('id_medicamento')

        # dosis_indicaciones: TEXT NOT NULL sin CHECK de longitud en el DDL
        self._validar_texto('dosis_indicaciones', 1_000)
