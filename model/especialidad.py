"""Tabla Especialidad: catálogo de especialidades médicas."""

from .constants import Entidad


class Especialidad(Entidad):
    """Especialidad que puede acreditar un médico o un enfermero."""

    _CAMPOS_CLAVE = ('id_esp',)

    def __init__(
        self,
        *,
        id_esp: int | None = None,
        nombre: str,
        descripcion: str | None = None,
    ) -> None:
        self.id_esp = id_esp
        self.nombre = nombre
        self.descripcion = descripcion

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_esp')

        # chk_esp_nombre
        self._validar_texto('nombre', 100)

        # descripcion es TEXT sin CHECK de longitud en el DDL
        if self.descripcion is not None and not self.descripcion.strip():
            self._fallar('descripcion', self.descripcion, "si se captura, no puede estar vacía")
