"""Autenticación del sistema: hash de contraseñas con bcrypt, registro e ingreso.

`Usuario.hash_contrasena`:

    $2b$12$vv3iPEmwKbXchLvQVxij8O qepa5iccMYHXM3kLmr8dcp5Fdn4Rj8u
    └┬┘ └┬┘ └──────── 22 ────────┘ └──────────── 31 ────────────┘
   algoritmo costo         salt                   hash

"""

import uuid
from .sesion import  SesionServicio,Sesion
import bcrypt

from model.constants import Roles
from model.usuario import Usuario
from model.repositories.usuario import UsuarioRepositorio
from .sesion_repositorio import SesionRepositorio


COSTO_BCRYPT = 12
"""
--- bcrypt hace 2^12 rondas, ~0.35 s por hash en esta máquina.

Entre más alto, más caro es para un atacante probar contraseñas por fuerza
bruta, y más tarda el login. 12 es el valor recomendado hoy; subirlo no rompe
los hashes viejos, porque cada hash trae su propio costo anotado adentro.
"""

LONGITUD_MINIMA_CONTRASENA = 8

MAXIMO_BYTES_CONTRASENA = 72 

_HASH_SENUELO = "$2b$12$uChxZ/EXwmtHWp8Va/Icre9CMYhOe/IlLzQSS.D6RFHRLA3bnY1LG"
"""Hash de descarte que se verifica cuando el correo no existe. Para evitar ataques de fuerza bruta"""

_ERROR_CREDENCIALES = "Usuario no válido, valida el correo o la contraseña." # mensaje de error





class Auth:
    """Puerta de entrada al sistema: registra usuarios y valida credenciales."""

    def __init__(self, usuario_repo: UsuarioRepositorio,sesion_repo:SesionRepositorio) -> None:
        self.__usuario_repo = usuario_repo
        self.__sesion_repo = sesion_repo



    @staticmethod
    def hashear(contrasena: str) -> str:
        """
        Devuelve el hash bcrypt (con su salt adentro) de la contraseña.
        """
        Auth._validar_contrasena(contrasena)
        hash_en_bytes = bcrypt.hashpw(
            contrasena.encode("utf-8"), bcrypt.gensalt(COSTO_BCRYPT)
        )
        return hash_en_bytes.decode("utf-8")

    @staticmethod
    def verificar(contrasena: str, hash_contrasena: str) -> bool:
        """
        Dice si la contraseña en crudo corresponde al hash guardado.
        """

        if not contrasena or not hash_contrasena:
            return False
        try:
            return bcrypt.checkpw(
                contrasena.encode("utf-8"), hash_contrasena.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _validar_contrasena(contrasena: str) -> None:
        """Reglas mínimas de la contraseña en claro, antes de hashearla."""
        if not isinstance(contrasena, str):
            raise ValueError("La contraseña debe ser texto.")
        if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
            raise ValueError(
                f"La contraseña debe tener al menos "
                f"{LONGITUD_MINIMA_CONTRASENA} caracteres."
            )
        if len(contrasena.encode("utf-8")) > MAXIMO_BYTES_CONTRASENA:
            raise ValueError(
                f"La contraseña no puede pasar de "
                f"{MAXIMO_BYTES_CONTRASENA} bytes (límite de bcrypt)."
            )

    @staticmethod
    def _normalizar_correo(correo: str) -> str:
        """Minúsculas y sin espacios: el correo se compara tal cual en el SELECT."""
        if not isinstance(correo, str):
            raise ValueError("El correo debe ser texto.")
        return correo.strip().lower()

    # -------------------------------------
    # Inicio de sesion y registro
    # -------------------------------------




    def registrar(self, correo: str, contrasena: str, rol: Roles) -> Usuario:
        """
        Da de alta un usuario nuevo y devuelve la entidad ya persistida.
        """
        correo_normalizado = self._normalizar_correo(correo)

        if self.__usuario_repo.obtener_por_correo(correo_normalizado):
            raise ValueError("Ya existe un usuario registrado con ese correo.")

        usuario = Usuario(
            id=str(uuid.uuid4()),
            hash_contrasena=self.hashear(contrasena),
            correo=correo_normalizado,
            rol=rol,
        )
        return self.__usuario_repo.registrar(usuario)

    def ingresar(self, correo: str, contrasena: str) -> Sesion:
        """
        Valida las credenciales y abre una sesión.
        """
        usuario_encontrado = self.__usuario_repo.obtener_por_correo(
            self._normalizar_correo(correo)
        )

        if not usuario_encontrado:
            self.verificar(contrasena, _HASH_SENUELO)
            raise ValueError(_ERROR_CREDENCIALES)

        if not self.verificar(contrasena, usuario_encontrado.hash_contrasena):
            raise ValueError(_ERROR_CREDENCIALES)

        sesion = SesionServicio.crear(usuario_encontrado)
        self.__sesion_repo.guardar(sesion)

        # Un usuario dado de baja no entra. Se comprueba DESPUÉS de verificar la
        # contraseña y con el mismo mensaje genérico, a propósito: si se
        # respondiera antes o distinto, cualquiera podría averiguar qué correos
        # están registrados y cuáles fueron desactivados, que es justo lo que
        # evita el hash señuelo de más arriba.
        if not usuario_encontrado.activo:
            raise ValueError(_ERROR_CREDENCIALES)

        return SesionServicio.crear(usuario_encontrado)

    def cambiar_contrasena(
        self, usuario: Usuario, contrasena_actual: str, contrasena_nueva: str
    ) -> Usuario:
        """Reemplaza el hash del usuario, exigiendo primero la contraseña vigente."""
        if not self.verificar(contrasena_actual, usuario.hash_contrasena):
            raise ValueError("La contraseña actual no es correcta.")

        usuario.hash_contrasena = self.hashear(contrasena_nueva)
        self.__usuario_repo.guardar(usuario)
        return usuario

    
