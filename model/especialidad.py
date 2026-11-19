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

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Especialidad:
            self._validar_propiedades()

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_esp')

        self._validar_texto('nombre', 100)

        if self.descripcion is not None and not self.descripcion.strip():
            self._fallar('descripcion', self.descripcion, "si se captura, no puede estar vacía")
