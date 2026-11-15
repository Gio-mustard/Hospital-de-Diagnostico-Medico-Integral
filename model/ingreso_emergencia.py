"""Tabla IngresoEmergencia."""

from datetime import datetime

from .atencion_medica import AtencionMedica
from .constants import NivelesUrgencia


class IngresoEmergencia(AtencionMedica):
    """Atención de urgencias, sin cita previa y clasificada por triage."""

    _CAMPOS_CLAVE = ('id_ingreso_emergencia',)

    def __init__(
        self,
        *,
        id_ingreso_emergencia: int | None = None,
        id_paciente: int,
        id_medico: int,
        fecha_hora: datetime | str,
        motivo: str,
        nivel_urgencia: NivelesUrgencia | str,
        diagnostico: str | None = None,
        id_recepcionista: int | None = None,
        num_habitacion: int | None = None,
    ) -> None:
        super().__init__(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=fecha_hora,
            motivo=motivo,
            diagnostico=diagnostico,
            id_recepcionista=id_recepcionista,
        )
        self.id_ingreso_emergencia = id_ingreso_emergencia
        self.num_habitacion = num_habitacion
        self.nivel_urgencia = nivel_urgencia

    @property
    def ubicacion(self) -> int | None:
        return self.num_habitacion

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_ingreso_emergencia')
        self._validar_llave_foranea('num_habitacion', opcional=True)

        # chk_emergencia_nivel
        self._validar_enum('nivel_urgencia', NivelesUrgencia)
