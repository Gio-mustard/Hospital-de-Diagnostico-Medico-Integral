"""Tabla DerechoHabiente: la raíz de la jerarquía de personas."""

from datetime import date

from .constants import (
    FECHA_NACIMIENTO_MINIMA,
    LONGITUD_UUID,
    PATRON_CODIGO_POSTAL,
    PATRON_CURP,
    PATRON_TELEFONO,
    Entidad,
    Generos,
)


class DerechoHabiente(Entidad):
    """Persona registrada en el hospital, sea paciente o personal.

    De ella heredan `Paciente`, `Trabajador` y `Recepcionista`, que en el DDL
    son tablas con un `id_derechohabiente NOT NULL UNIQUE`: una especialización
    uno a uno.

    NO hereda de `Usuario`: en el DDL la tabla DerechoHabiente no tiene las
    columnas de credenciales (`hash_contrasena`, `correo`, `rol`), sino una FK
    opcional al usuario que puede iniciar sesión como esta persona. Esa
    relación es `auth_user_id`, que se valida más abajo. Una persona no ES un
    usuario del sistema: TIENE uno, y puede no tenerlo (un paciente que nunca
    entra a la app).

    El campo `activo` se declara aquí y nada más aquí. Las tablas hijas repiten
    la columna `activo`, pero el repositorio escribe en todas el mismo valor
    heredado en lugar de mantener banderas que se puedan contradecir.
    """

    _CAMPOS_CLAVE = ('id_derechohabiente',)

    def __init__(
        self,
        *,
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
        self.id_derechohabiente = id_derechohabiente
        self.auth_user_id = auth_user_id
        self.nombres = nombres
        self.apellido_paterno = apellido_paterno
        self.apellido_materno = apellido_materno
        self.direccion_calle = direccion_calle
        self.codigo_postal = codigo_postal
        self.ciudad = ciudad
        self.estado = estado
        self.fecha_nacimiento = fecha_nacimiento
        self.genero = genero
        self.telefono = telefono
        self.curp = curp
        self.activo = activo

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is DerechoHabiente:
            self._validar_propiedades()


    @property
    def nombre_completo(self) -> str:
        partes = (self.nombres, self.apellido_paterno, self.apellido_materno)
        return " ".join(parte for parte in partes if parte)

    @property
    def edad(self) -> int:
        nacimiento: date = date.fromisoformat(self.fecha_nacimiento) if isinstance(self.fecha_nacimiento, str) else self.fecha_nacimiento
        hoy = self._hoy()
        cumplio = (hoy.month, hoy.day) >= (nacimiento.month, nacimiento.day)
        return hoy.year - nacimiento.year - (0 if cumplio else 1)

    
    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_derechohabiente')

        
        self._validar_texto('nombres', 100)
        self._validar_texto('apellido_paterno', 100)
        self._validar_texto('apellido_materno', 100, opcional=True)
        self._validar_texto('direccion_calle', 100)
        self._validar_texto('ciudad', 50)
        self._validar_texto('estado', 50)

        self._validar_texto('auth_user_id', LONGITUD_UUID, opcional=True)
        if self.auth_user_id is not None and len(self.auth_user_id) != LONGITUD_UUID:
            self._fallar(
                'auth_user_id', self.auth_user_id, f"debe medir exactamente {LONGITUD_UUID} caracteres"
            )

        self._validar_patron('codigo_postal', PATRON_CODIGO_POSTAL, "5 dígitos")

        self._validar_fecha(
            'fecha_nacimiento', minima=FECHA_NACIMIENTO_MINIMA, maxima=self._hoy()
        )

        
        self._validar_enum('genero', Generos, opcional=True)

        
        self._validar_patron(
            'telefono', PATRON_TELEFONO, "E.164, por ejemplo '+526866024822'", opcional=True
        )

        self._validar_patron('curp', PATRON_CURP, "18 caracteres de CURP en mayúsculas")

        self._validar_booleano('activo')
