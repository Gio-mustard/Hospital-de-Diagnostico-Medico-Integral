"""Persistencia de las sesiones abiertas: la tabla `sesiones`."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256

from model.constants import Roles
from model.database import Database
from model.repositories.usuario import UsuarioRepositorio

from .sesion import Sesion

TABLA = "sesiones"

COLUMNAS = (
    "id",
    "usuario_id",
    "token_hash",
    "fecha_creacion",
    "fecha_expiracion",
    "fecha_revocacion",
    "dispositivo",
    "rol",
)

CLAVE = ("id",)


def hashear_token(token: str) -> str:
    """Devuelve el SHA-256 en hexadecimal del token, que es lo que se guarda."""
    if not isinstance(token, str) or not token:
        raise ValueError("El token de la sesión debe ser texto no vacío.")
    return sha256(token.encode("utf-8")).hexdigest()


def _a_texto(momento: datetime | None) -> str | None:
    """Pasa un `datetime` al TEXT ISO 8601 UTC que espera la columna.

    Un `datetime` sin zona se toma como UTC en lugar de rechazarlo, porque es
    el descuido más común y suponer otra cosa correría la hora. Los
    microsegundos se van: la columna guarda segundos.
    """
    if momento is None:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _a_momento(texto: str | None) -> datetime | None:
    """Inverso de `_a_texto`: del TEXT de la columna a un `datetime` con zona."""
    if texto is None:
        return None
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento


class SesionRepositorio(ABC):
    """Contrato del repositorio de sesiones.

    Son tres operaciones, no las cinco del resto de los repositorios, porque
    una sesión no se administra como las demás entidades: se abre, se cierra y
    se consulta por token. No hay `obtener_todos` ni `obtener_por_id` a
    propósito; nadie en el sistema tiene por qué listar las sesiones ajenas, y
    no exponerlo es una línea de defensa gratis.
    """

    @abstractmethod
    def guardar(self, sesion: Sesion) -> None:
        """Persiste la sesión recibida (inserta la nueva, actualiza la que ya está)."""
        ...

    @abstractmethod
    def revocar(self, sesion: Sesion) -> None:
        """Cierra la sesión recibida, marcándole la fecha de revocación."""
        ...

    @abstractmethod
    def obtener_activa(self, token: str) -> Sesion | None:
        """Devuelve la sesión viva que corresponde al token, o None."""
        ...


class SesionSQLRepositorio(SesionRepositorio):
    """Repositorio de sesiones sobre SQLite.

    Recibe el repositorio de usuarios además de la base de datos porque una
    `Sesion` lleva adentro el `Usuario` completo, y la tabla `sesiones` solo
    guarda su id: para rearmar la entidad hay que ir por la persona a su propio
    repositorio. Se inyecta la interfaz, no la implementación, para que las
    pruebas puedan pasar un doble.
    """

    def __init__(self, db: Database, usuario_repo: UsuarioRepositorio) -> None:
        super().__init__()
        self.__db = db
        self.__usuario_repo = usuario_repo

    @property
    def db(self) -> Database:
        """Base de datos inyectada en el repositorio."""
        return self.__db

    @staticmethod
    def _ahora() -> str:
        """El momento actual, ya en el formato de las columnas de fecha."""
        texto = _a_texto(datetime.now(timezone.utc))
        assert texto is not None
        return texto

    @staticmethod
    def _a_fila(sesion: Sesion) -> dict:
        """Convierte una Sesion en columna -> valor listo para SQLite."""
        return {
            "id": sesion.id,
            "usuario_id": sesion.usuario.id,
            "token_hash": hashear_token(sesion.token),
            "fecha_creacion": _a_texto(sesion.fecha_creacion),
            "fecha_expiracion": _a_texto(sesion.fecha_expiracion),
            "fecha_revocacion": _a_texto(sesion.fecha_revocacion),
            "dispositivo": sesion.dispositivo,
            "rol": sesion.rol.value if isinstance(sesion.rol, Enum) else sesion.rol,
        }

    def _a_entidad(self, row, token: str) -> Sesion | None:
        """Rearma la Sesion de un renglón, con el token que presentó quien pregunta.

        El token se recibe en lugar de leerse de la fila porque en la fila no
        está: ahí solo vive su hash, y de un hash no se regresa. Quien llega
        con el token correcto es justamente el único que puede volver a poner
        ese dato en la entidad.

        Devuelve None si el usuario de la sesión ya no existe: sin persona no
        hay `Sesion` que armar. Si existe pero está dado de baja, la sesión se
        devuelve igual; hacer valer `activo` le toca a `Auth`, igual que al
        iniciar sesión.
        """
        usuario = self.__usuario_repo.obtener_por_id(row["usuario_id"])
        if usuario is None:
            return None

        return Sesion(
            id=row["id"],
            rol=Roles(row["rol"]),
            usuario=usuario,
            token=token,
            fecha_creacion=_a_momento(row["fecha_creacion"]),
            fecha_expiracion=_a_momento(row["fecha_expiracion"]),
            fecha_revocacion=_a_momento(row["fecha_revocacion"]),
            dispositivo=row["dispositivo"],
        )

    def guardar(self, sesion: Sesion) -> None:
        """Inserta la sesión, o actualiza la que ya tiene ese id (upsert por id).

        El conflicto solo actualiza las columnas que de verdad cambian a lo
        largo de la vida de una sesión: su vencimiento y su revocación. El
        token_hash y la fecha de creación se quedan como se escribieron, porque
        un token distinto es otra sesión, no la misma modificada.

        Que el usuario exista lo hace valer la llave foránea de la tabla, con
        `PRAGMA foreign_keys = ON` encendido por la conexión: un usuario_id que
        no está en Usuario revienta con IntegrityError en lugar de dejar una
        sesión huérfana. Y la columna UNIQUE de token_hash hace lo mismo si dos
        sesiones distintas llegaran con el mismo token.
        """
        if not sesion.usuario:
            raise ValueError("Un usuario es necesario para crear una sesion")
        if not sesion.usuario.id:
            raise ValueError("El usuario de la sesión no tiene id: no se ha persistido.")
        if not sesion.id:
            raise ValueError("La sesión no tiene id.")

        fila = self._a_fila(sesion)
        marcadores = ", ".join("?" for _ in COLUMNAS)
        sql = (
            f"INSERT INTO {TABLA} ({', '.join(COLUMNAS)}) VALUES ({marcadores}) "
            f"ON CONFLICT ({', '.join(CLAVE)}) DO UPDATE SET "
            "fecha_expiracion = excluded.fecha_expiracion, "
            "fecha_revocacion = excluded.fecha_revocacion, "
            "dispositivo = excluded.dispositivo"
        )
        self.__db.execute(sql, tuple(fila[columna] for columna in COLUMNAS))

    def revocar(self, sesion: Sesion) -> None:
        """Marca la sesión como cerrada, poniéndole la fecha de revocación.

        El `fecha_revocacion IS NULL` del WHERE deja la operación idempotente:
        revocar dos veces no corre la hora del primer cierre, que es el dato
        que importa para una auditoría. Si la sesión no está en la tabla o ya
        estaba cerrada no pasa nada y no se avisa, porque el resultado que se
        pedía (que esa sesión no sirva) ya se cumple.

        La `Sesion` que se recibe no se toca: es un dataclass congelado y la
        verdad vive en la base. Quien necesite el estado nuevo lo pide con
        `obtener_activa`, que a partir de aquí devolverá None para ese token.
        """
        sql = (
            f"UPDATE {TABLA} SET fecha_revocacion = ? "
            "WHERE id = ? AND fecha_revocacion IS NULL"
        )
        self.__db.execute(sql, (self._ahora(), sesion.id))

    def obtener_activa(self, token: str) -> Sesion | None:
        """Devuelve la sesión viva de ese token, o None si no hay ninguna.

        Viva es las dos cosas a la vez: sin revocar y sin vencer. Las dos
        condiciones van en el SELECT y no en un `if` posterior, para que una
        sesión caduca ni siquiera llegue a armarse como entidad y no exista
        forma de usarla por descuido.

        Un token que no corresponde a nada devuelve None, igual que uno vencido:
        quien pregunta no se entera de cuál de los dos casos fue.
        """
        sql = (
            f"SELECT {', '.join(COLUMNAS)} FROM {TABLA} "
            "WHERE token_hash = ? AND fecha_revocacion IS NULL "
            "AND fecha_expiracion > ?"
        )
        row = self.__db.execute(sql, (hashear_token(token), self._ahora())).fetchone()
        return self._a_entidad(row, token) if row else None
