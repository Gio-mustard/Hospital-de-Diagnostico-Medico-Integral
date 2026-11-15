"""Tabla Paciente: especialización de DerechoHabiente."""

from datetime import date

from .constants import Generos, TiposSangre
from .derechohabiente import DerechoHabiente


class Paciente(DerechoHabiente):
    """Derechohabiente que recibe atención médica.

    La tabla solo agrega `tipo_sangre`; los datos personales se heredan, así que
    construir un `Paciente` desde la base de datos pide un JOIN entre
    `Paciente` y `DerechoHabiente`.
    """

    _CAMPOS_CLAVE = ('id_paciente',)

    def __init__(
        self,
        *,
        id_paciente: int | None = None,
        tipo_sangre: TiposSangre | str | None = None,
        id_derechohabiente: int | None = None,
        nombres: str,
        apellido_paterno: str,
        apellido_materno: str | None = None,
        direccion_calle: str,
        codigo_postal: str,
        ciudad: str,
        estado: str,
        fecha_nacimiento: date | str,
        genero: Generos | str | None = None,
        telefono: str | None = None,
        curp: str,
        activo: bool = True,
        auth_user_id: str | None = None,
    ) -> None:
        super().__init__(
            id_derechohabiente=id_derechohabiente,
            nombres=nombres,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            direccion_calle=direccion_calle,
            codigo_postal=codigo_postal,
            ciudad=ciudad,
            estado=estado,
            fecha_nacimiento=fecha_nacimiento,
            genero=genero,
            telefono=telefono,
            curp=curp,
            activo=activo,
            auth_user_id=auth_user_id,
        )
        self.id_paciente = id_paciente
        self.tipo_sangre = tipo_sangre

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_paciente')

        # La FK id_derechohabiente es NOT NULL UNIQUE, pero queda en None
        # mientras no se inserte al derechohabiente que le da origen.
        self._validar_llave_foranea('id_derechohabiente', opcional=True)

        # chk_paciente_sangre
        self._validar_enum('tipo_sangre', TiposSangre, opcional=True)
