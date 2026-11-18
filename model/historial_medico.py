"""Tabla HistorialMedico."""

from datetime import datetime

from .constants import LONGITUD_UUID, Entidad, TiposDocumento


class HistorialMedico(Entidad):
    """Documento clínico de un paciente, capturado por un médico.

    `datos_dinamicos` es el JSONB del DDL: `None` significa que el algoritmo de
    extracción todavía no lo procesó. `etiquetas` es el arreglo JSON de la
    columna del mismo nombre.
    """

    _CAMPOS_CLAVE = ('id_historial',)

    def __init__(
        self,
        *,
        id_historial: int | None = None,
        id_paciente: int,
        id_medico: int,
        fecha_registro: datetime | str,
        documento_url: str | None = None,
        tipo_documento: TiposDocumento | str = TiposDocumento.EXPEDIENTE_PDF,
        datos_dinamicos: dict | str | None = None,
        etiquetas: list | str | None = None,
        uuid_publico: str | None = None,
    ) -> None:
        self.id_historial = id_historial
        self.uuid_publico = uuid_publico
        self.id_paciente = id_paciente
        self.id_medico = id_medico
        self.fecha_registro = fecha_registro
        self.documento_url = documento_url
        self.tipo_documento = tipo_documento
        self.datos_dinamicos = datos_dinamicos
        self.etiquetas = [] if etiquetas is None else etiquetas

    @property
    def pendiente_de_procesar(self) -> bool:
        """Coincide con el índice parcial idx_historial_pendientes."""
        return self.datos_dinamicos is None

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_historial')
        self._validar_llave_foranea('id_paciente')
        self._validar_llave_foranea('id_medico')

        self._validar_texto('uuid_publico', LONGITUD_UUID, opcional=True)
        if self.uuid_publico is not None and len(self.uuid_publico) != LONGITUD_UUID:
            self._fallar(
                'uuid_publico', self.uuid_publico, f"debe medir {LONGITUD_UUID} caracteres"
            )

        self._validar_fecha_hora('fecha_registro')

        self._validar_url_https('documento_url', maximo=500, opcional=True)

        self._validar_enum('tipo_documento', TiposDocumento)

        self._validar_json('datos_dinamicos', dict, opcional=True)

        self._validar_json('etiquetas', list)

        if self.documento_url is None and not self.datos_dinamicos:
            self._fallar(
                'documento_url',
                self.documento_url,
                "el historial necesita una URL de documento o datos_dinamicos con contenido",
            )
