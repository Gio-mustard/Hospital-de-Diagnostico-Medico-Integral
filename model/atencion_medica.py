"""Clase abstracta compartida por Cita e IngresoEmergencia.

En el DDL las dos tablas comparten seis columnas con las mismas reglas:
`id_paciente`, `id_medico`, `id_recepcionista`, `fecha_hora`, `motivo` y
`diagnostico`. Se diferencian en dónde se atiende al paciente (consultorio o
habitación) y en la columna que las clasifica (`estado` o `nivel_urgencia`).
"""

from abc import abstractmethod
from datetime import datetime

from .constants import Entidad


class AtencionMedica(Entidad):
    """Encuentro entre un paciente y un médico en un momento dado.

    Es abstracta: quien hereda dice en qué espacio físico ocurre la atención
    (`ubicacion`).
    """

    def __init__(
        self,
        *,
        id_paciente: int,
        id_medico: int,
        fecha_hora: datetime | str,
        motivo: str,
        diagnostico: str | None = None,
        id_recepcionista: int | None = None,
    ) -> None:
        self.id_paciente = id_paciente
        self.id_medico = id_medico
        self.id_recepcionista = id_recepcionista
        self.fecha_hora = fecha_hora
        self.motivo = motivo
        self.diagnostico = diagnostico

    @property
    @abstractmethod
    def ubicacion(self) -> int | None:
        """Número del espacio físico donde se atiende, si ya se asignó."""

    @property
    def diagnosticada(self) -> bool:
        return self.diagnostico is not None

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_llave_foranea('id_paciente')
        self._validar_llave_foranea('id_medico')
        self._validar_llave_foranea('id_recepcionista', opcional=True)

        # chk_cita_fecha / chk_emergencia_fecha
        self._validar_fecha_hora('fecha_hora')

        # motivo: TEXT NOT NULL sin CHECK de longitud en el DDL
        self._validar_texto('motivo', 1_000)

        if self.diagnostico is not None and not self.diagnostico.strip():
            self._fallar('diagnostico', self.diagnostico, "si se captura, no puede estar vacío")
