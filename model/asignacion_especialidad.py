"""Tablas MedicoEspecialidad y EnfermeroEspecialidad.

Las dos tablas del DDL son idénticas salvo por la FK del titular: misma llave
primaria compuesta, mismo `documentos` con CHECK de URL y mismo `institucion`
limitado a 150 caracteres. Esa parte repetida vive una sola vez en la clase
abstracta `AsignacionEspecialidad`.
"""

from abc import abstractmethod
from typing import ClassVar

from .constants import Entidad

LONGITUD_MAXIMA_INSTITUCION = 150


class AsignacionEspecialidad(Entidad):
    """Relación muchos a muchos entre un profesional y una especialidad.

    Es abstracta: quien hereda dice a qué columna apunta el titular
    (`_CAMPO_TITULAR`) y cómo leerla (`id_titular`).
    """

    _CAMPO_TITULAR: ClassVar[str]

    def __init__(
        self,
        *,
        id_esp: int,
        documentos: str | None = None,
        institucion: str | None = None,
    ) -> None:
        self.id_esp = id_esp
        self.documentos = documentos
        self.institucion = institucion

    @property
    @abstractmethod
    def id_titular(self) -> int:
        """FK del profesional dueño de la asignación."""

    @property
    def acreditada(self) -> bool:
        """¿La asignación trae el documento que la respalda?"""
        return self.documentos is not None

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_llave_foranea(self._CAMPO_TITULAR)
        self._validar_llave_foranea('id_esp')

        self._validar_url_https('documentos', opcional=True)

        self._validar_texto('institucion', LONGITUD_MAXIMA_INSTITUCION, opcional=True)


class MedicoEspecialidad(AsignacionEspecialidad):
    """Tabla MedicoEspecialidad. PK compuesta (id_medico, id_esp)."""

    _CAMPOS_CLAVE = ('id_medico', 'id_esp')
    _CAMPO_TITULAR = 'id_medico'

    def __init__(
        self,
        *,
        id_medico: int,
        id_esp: int,
        documentos: str | None = None,
        institucion: str | None = None,
    ) -> None:
        super().__init__(id_esp=id_esp, documentos=documentos, institucion=institucion)
        self.id_medico = id_medico

    @property
    def id_titular(self) -> int:
        return self.id_medico


class EnfermeroEspecialidad(AsignacionEspecialidad):
    """Tabla EnfermeroEspecialidad. PK compuesta (id_enfermero, id_esp)."""

    _CAMPOS_CLAVE = ('id_enfermero', 'id_esp')
    _CAMPO_TITULAR = 'id_enfermero'

    def __init__(
        self,
        *,
        id_enfermero: int,
        id_esp: int,
        documentos: str | None = None,
        institucion: str | None = None,
    ) -> None:
        super().__init__(id_esp=id_esp, documentos=documentos, institucion=institucion)
        self.id_enfermero = id_enfermero

    @property
    def id_titular(self) -> int:
        return self.id_enfermero
