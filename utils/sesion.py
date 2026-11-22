import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import keyring
from keyring.errors import PasswordDeleteError

from model.constants import Roles
from model.usuario import Usuario
from abc import ABC,abstractmethod

DURACION_SESION = timedelta(hours=8)
"""Cuánto vive una sesión desde que se abre.

Un turno de trabajo. Al vencerse hay que volver a escribir la contraseña,
aunque la computadora se haya quedado prendida en el consultorio.
"""

BYTES_TOKEN = 32
"""256 bits de azar. Es el tamaño que hace inútil intentar adivinar un token."""

RAIZ = Path(__file__).resolve().parent.parent

ARCHIVO_TOKEN_PRUEBAS = RAIZ / "sesion_prueba.txt"
"""Dónde escribe el token el servicio de pruebas. Va en .gitignore."""


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


class SesionServicio(ABC):
    @classmethod
    @abstractmethod
    def guardar(cls,token:str)->None:
        """Guarda el token crudo de la sesion"""
        ...

    @classmethod
    @abstractmethod
    def limpiar(cls)->None:
        "Borra el token de sesion"
        ...

    @classmethod
    @abstractmethod
    def cargar(cls)->str|None:
        """Lee y retorta el token crudo de la sesion"""
        ...


    @classmethod
    def crear(cls,usuario:Usuario)->Sesion:
        """Crea una sesión nueva para el usuario recibido.
    
            Solo arma la entidad, con su token y sus fechas. Guardarla en la tabla
            le toca a `SesionRepositorio.guardar`, y poner el token en el llavero a
            `SesionServicio.guardar`: quien ingresa decide si esta sesión se
            persiste o es de un solo uso.
        """
        return Sesion(id=uuid.uuid4().hex, rol=usuario.rol, usuario=usuario)
    

class SesionServicioKeyring(SesionServicio):

    NOMBRE_SERVICIO = 'hdmi-app'
    CLAVE_TOKEN = 'tokencito'

    @classmethod
    def guardar(cls,token:str)->None:
        keyring.set_password(cls.NOMBRE_SERVICIO,cls.CLAVE_TOKEN,token)

    @classmethod
    def limpiar(cls) -> None:
        """Borra el token del llavero. No se queja si no había ninguno.

        `keyring.delete_password` lanza `PasswordDeleteError` cuando no hay nada
        que borrar, y eso convertiría en un error algo que no lo es: cerrar una
        sesión que ya estaba cerrada tiene que dar lo mismo que cerrarla una
        vez. `Auth.cerrar_sesion` depende de esto, porque limpia el llavero
        incluso cuando no encontró sesión que revocar.
        """
        try:
            keyring.delete_password(cls.NOMBRE_SERVICIO, cls.CLAVE_TOKEN)
        except PasswordDeleteError:
            pass

    @classmethod
    def cargar(cls)->str|None:
        """Retorna el token crudo guardado"""
        return keyring.get_password(cls.NOMBRE_SERVICIO,cls.CLAVE_TOKEN)

    

class SesionServicioArchivo(SesionServicio):
    """El mismo servicio, pero el token se guarda en un .txt en lugar del llavero. !!! SOLO PARA PRUEBAS !!!"""

    ARCHIVO = ARCHIVO_TOKEN_PRUEBAS

    @classmethod
    def guardar(cls, token: str) -> None:
        """Escribe el token en el archivo, reemplazando el que hubiera."""
        if not isinstance(token, str) or not token:
            raise ValueError("El token de la sesión debe ser texto no vacío.")

        # touch antes de escribir para que el archivo nazca con los permisos
        # recortados: si se creara con write_text, existiría un instante
        # legible por cualquiera en la máquina.
        cls.ARCHIVO.touch(mode=0o600, exist_ok=True)
        cls.ARCHIVO.write_text(token, encoding="utf-8")

    @classmethod
    def cargar(cls) -> str | None:
        """Devuelve el token guardado, o None si no hay archivo.

        Un archivo vacío o con puros espacios cuenta como no haber nada: es el
        estado en que queda si alguien lo deja a medias editándolo a mano, y
        devolver "" haría que el repositorio buscara una sesión con token vacío
        en lugar de pedir la contraseña.
        """
        if not cls.ARCHIVO.exists():
            return None
        token = cls.ARCHIVO.read_text(encoding="utf-8").strip()
        return token or None

    @classmethod
    def limpiar(cls) -> None:
        """Borra el archivo. No se queja si no estaba: cerrar sesión dos veces
        tiene que dar lo mismo que cerrarla una."""
        cls.ARCHIVO.unlink(missing_ok=True)

