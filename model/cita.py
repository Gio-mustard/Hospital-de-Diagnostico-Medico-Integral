"""Tabla Cita."""

from datetime import datetime

from .atencion_medica import AtencionMedica
from .constants import EstadosCita


class Cita(AtencionMedica):
    """Consulta externa agendada en un consultorio."""

    _CAMPOS_CLAVE = ('id_cita',)

    def __init__(
        self,
        *,
        id_cita: int | None = None,
        id_paciente: int,
        id_medico: int,
        fecha_hora: datetime | str,
        motivo: str,
        estado: EstadosCita | str = EstadosCita.PROGRAMADA,
        diagnostico: str | None = None,
        id_recepcionista: int | None = None,
        num_consultorio: int | None = None,
    ) -> None:
        super().__init__(
            id_paciente=id_paciente,
            id_medico=id_medico,
            fecha_hora=fecha_hora,
            motivo=motivo,
            diagnostico=diagnostico,
            id_recepcionista=id_recepcionista,
        )
        self.id_cita = id_cita
        self.num_consultorio = num_consultorio
        self.estado = estado

    @property
    def ubicacion(self) -> int | None:
        return self.num_consultorio

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_cita')
        self._validar_llave_foranea('num_consultorio', opcional=True)

        # chk_cita_estado
        self._validar_enum('estado', EstadosCita)

        # chk_cita_diagnostico_coherente: el diagnóstico existe si y solo si la
        # cita quedó Completada.
        completada = self.estado is EstadosCita.COMPLETADA
        if completada and self.diagnostico is None:
            self._fallar(
                'diagnostico', self.diagnostico, "una cita Completada necesita diagnóstico"
            )
        if not completada and self.diagnostico is not None:
            self._fallar(
                'diagnostico',
                self.diagnostico,
                f"solo una cita Completada puede traer diagnóstico (estado: {self.estado.value})",
            )
