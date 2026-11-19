"""Tabla Recepcionista: especialización de DerechoHabiente."""

from datetime import date

from .constants import Generos, Turnos
from .derechohabiente import DerechoHabiente


class Recepcionista(DerechoHabiente):
    """Quien agenda citas y registra ingresos.

    Hereda de `DerechoHabiente` y no de `Trabajador` porque en el DDL la tabla
    trae `id_derechohabiente NOT NULL` y un `id_trabajador UNIQUE` que acepta
    NULL: una recepcionista puede existir sin estar dada de alta como
    trabajadora. Por eso `id_trabajador` es un simple atributo opcional.
    """

    _CAMPOS_CLAVE = ('id_recepcionista',)

    def __init__(
        self,
        *,
        id_recepcionista: int | None = None,
        turno: Turnos | str = Turnos.MATUTINO,
        modulo_atencion: str = 'Admisión Principal',
        extension_tel: str | None = None,
        id_trabajador: int | None = None,
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
        self.id_recepcionista = id_recepcionista
        self.id_trabajador = id_trabajador
        self.turno = turno
        self.modulo_atencion = modulo_atencion
        self.extension_tel = extension_tel

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Recepcionista:
            self._validar_propiedades()

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_recepcionista')
        self._validar_llave_foranea('id_derechohabiente', opcional=True)
        self._validar_llave_foranea('id_trabajador', opcional=True)

        self._validar_enum('turno', Turnos)

        self._validar_texto('modulo_atencion', 50)
        self._validar_texto('extension_tel', 10, opcional=True)
