"""Tabla Enfermero: especialización de Trabajador."""

from datetime import date

from .constants import Generos
from .trabajador import Trabajador


class Enfermero(Trabajador):
    """Trabajador del área de enfermería.

    La tabla no agrega columnas propias más allá de su llave y la FK al
    trabajador: toda la información vive en las clases de las que hereda. Se
    modela aparte porque `EnfermeroEspecialidad` apunta a `id_enfermero`.
    """

    _CAMPOS_CLAVE = ('id_enfermero',)

    def __init__(
        self,
        *,
        id_enfermero: int | None = None,
        id_trabajador: int | None = None,
        numero_empleado: str,
        departamento: str,
        fecha_ingreso: date | str,
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
            id_trabajador=id_trabajador,
            numero_empleado=numero_empleado,
            departamento=departamento,
            fecha_ingreso=fecha_ingreso,
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
        self.id_enfermero = id_enfermero

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Enfermero:
            self._validar_propiedades()

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_enfermero')
        self._validar_llave_foranea('id_trabajador', opcional=True)
