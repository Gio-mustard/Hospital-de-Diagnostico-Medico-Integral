import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import keyring

from model.constants import Roles
from model.usuario import Usuario

DURACION_SESION = timedelta(hours=8)
"""Cuánto vive una sesión desde que se abre.

Un turno de trabajo. Al vencerse hay que volver a escribir la contraseña,
aunque la computadora se haya quedado prendida en el consultorio.
"""

BYTES_TOKEN = 32
"""256 bits de azar. Es el tamaño que hace inútil intentar adivinar un token."""


def ahora_utc() -> datetime:
    """Momento actual en UTC, sin microsegundos (las columnas guardan segundos)."""
    return datetime.now(timezone.utc).replace(microsecond=0)


@dataclass(frozen=True)
class Sesion:
    """Sesión abierta de un usuario ya autenticado.

    `id` NO es el id del usuario: es el identificador de *esta* sesión, para
    poder distinguir dos ingresos del mismo usuario y cerrar uno sin tocar al
    otro. El id del usuario se llega por `sesion.usuario.id`.

    `token` es la credencial que el cliente presenta en cada operación, y es el
    único dato de aquí que no se guarda tal cual: la tabla `sesiones` solo
    conserva su SHA-256 (ver `SesionSQLRepositorio`). Se genera solo, para que
    nadie tenga que acordarse de hacerlo, y queda fuera del `repr` para que no
    se escape en un log o en un traceback.

    `fecha_expiracion` se puede dar explícita si una sesión necesita durar
    distinto; si no se da, es la creación más `DURACION_SESION`.

    Congelada a propósito: una sesión no se modifica. Cerrarla es escribir su
    revocación en la base (`SesionRepositorio.revocar`), y lo que vale después
    de eso es lo que diga la tabla, no este objeto.
    """

    id: str
    rol: Roles
    usuario: Usuario
    token: str = field(
        default_factory=lambda: secrets.token_urlsafe(BYTES_TOKEN), repr=False
    )
    fecha_creacion: datetime = field(default_factory=ahora_utc)
    fecha_expiracion: datetime | None = None
    fecha_revocacion: datetime | None = None
    dispositivo: str | None = None

    def __post_init__(self) -> None:
        # object.__setattr__ porque el dataclass está congelado: es la forma de
        # calcular un campo derivado de otro sin abrirle la mano al resto.
        if self.fecha_expiracion is None:
            object.__setattr__(
                self, "fecha_expiracion", self.fecha_creacion + DURACION_SESION
            )

    @property
    def revocada(self) -> bool:
        return self.fecha_revocacion is not None

    @property
    def expirada(self) -> bool:
        return self.fecha_expiracion is not None and ahora_utc() >= self.fecha_expiracion

    @property
    def activa(self) -> bool:
        """Sin revocar y sin vencer: las dos cosas a la vez."""
        return not (self.revocada or self.expirada)


class SesionServicio():

    NOMBRE_SERVICIO = 'hdmi-app'
    CLAVE_TOKEN = 'tokencito'

    @classmethod
    def guardar(cls,token:str)->None:
        keyring.set_password(cls.NOMBRE_SERVICIO,cls.CLAVE_TOKEN,token)

    @classmethod
    def limpiar(cls)->None:
        keyring.delete_password(cls.NOMBRE_SERVICIO,cls.CLAVE_TOKEN)

    @classmethod
    def cargar(cls)->str|None:
        return keyring.get_password(cls.NOMBRE_SERVICIO,cls.CLAVE_TOKEN)

    @classmethod
    def crear(cls,usuario:Usuario)->Sesion:
        """Crea una sesión nueva para el usuario recibido.

        Solo arma la entidad, con su token y sus fechas. Guardarla en la tabla
        le toca a `SesionRepositorio.guardar`, y poner el token en el llavero a
        `SesionServicio.guardar`: quien ingresa decide si esta sesión se
        persiste o es de un solo uso.
        """
        return Sesion(id=uuid.uuid4().hex, rol=usuario.rol, usuario=usuario)
