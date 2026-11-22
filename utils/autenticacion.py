"""Autenticación del sistema: hash de contraseñas con bcrypt, registro e ingreso.

`Usuario.hash_contrasena`:

    $2b$12$vv3iPEmwKbXchLvQVxij8O qepa5iccMYHXM3kLmr8dcp5Fdn4Rj8u
    └┬┘ └┬┘ └──────── 22 ────────┘ └──────────── 31 ────────────┘
   algoritmo costo         salt                   hash

"""

import uuid

import bcrypt

from model.constants import Roles
from model.usuario import Usuario
from model.repositories.usuario import UsuarioRepositorio

from .sesion import Sesion, SesionServicio
from .sesion_repositorio import SesionRepositorio


COSTO_BCRYPT = 12
"""
--- bcrypt hace 2^12 rondas, ~0.35 s por hash en esta máquina.

Entre más alto, más caro es para un atacante probar contraseñas por fuerza
bruta, y más tarda el login. 12 es el valor recomendado hoy; subirlo no rompe
los hashes viejos, porque cada hash trae su propio costo anotado adentro.
"""





class AuthService:

    __LONGITUD_MINIMA_CONTRASENA = 8
    __MAXIMO_BYTES_CONTRASENA = 72 
    __HASH_SENUELO = "$2b$12$uChxZ/EXwmtHWp8Va/Icre9CMYhOe/IlLzQSS.D6RFHRLA3bnY1LG"
    __ERROR_CREDENCIALES = "Usuario no válido, valida el correo o la contraseña." # mensaje de error

    """Puerta de entrada al sistema: registra usuarios y valida credenciales."""

    def __init__(
        self,
        usuario_repo: UsuarioRepositorio,
        sesion_repo: SesionRepositorio,
        sesion_servicio:SesionServicio
    ) -> None:
        self.__usuario_repo = usuario_repo
        self.__sesion_repo = sesion_repo
        self.__sesion_servicio = sesion_servicio

    @staticmethod
    def hashear(contrasena: str) -> str:
        """
        Devuelve el hash bcrypt (con su salt adentro) de la contraseña.
        """
        AuthService._validar_contrasena(contrasena)
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
        if len(contrasena) < AuthService.__LONGITUD_MINIMA_CONTRASENA:
            raise ValueError(
                f"La contraseña debe tener al menos "
                f"{AuthService.__LONGITUD_MINIMA_CONTRASENA} caracteres."
            )
        if len(contrasena.encode("utf-8")) > AuthService.__MAXIMO_BYTES_CONTRASENA:
            raise ValueError(
                f"La contraseña no puede pasar de "
                f"{AuthService.__MAXIMO_BYTES_CONTRASENA} bytes (límite de bcrypt)."
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
            id=uuid.uuid4().hex,
            hash_contrasena=self.hashear(contrasena),
            correo=correo_normalizado,
            rol=rol,
        )
        return self.__usuario_repo.registrar(usuario)

    def ingresar(
        self, correo: str, contrasena: str, *, recordar: bool = False
    ) -> Sesion:
        """Valida las credenciales, abre una sesión y la persiste."""
        usuario_encontrado = self.__usuario_repo.obtener_por_correo(
            self._normalizar_correo(correo)
        )

        if not usuario_encontrado:
            self.verificar(contrasena, self.__HASH_SENUELO)
            raise ValueError(self.__ERROR_CREDENCIALES)

        if not self.verificar(contrasena, usuario_encontrado.hash_contrasena):
            raise ValueError(self.__ERROR_CREDENCIALES)

        
        if not usuario_encontrado.activo:
            raise ValueError(self.__ERROR_CREDENCIALES)

        sesion = self.__sesion_servicio.crear(usuario_encontrado)
        self.__sesion_repo.guardar(sesion)

        if recordar:
            self.__sesion_servicio.guardar(sesion.token)

        return sesion

    # ----------------------------------------
    # Manejo de sesiones
    # ----------------------------------------

    def restaurar_sesion(self)->Sesion|None:
        """Restaura y retorna la sesion si existe"""
        token = self.__sesion_servicio.cargar()

        if token is None : return None

        sesion:Sesion|None = self.__sesion_repo.obtener_activa(token)

        if sesion is None:
            # Si el usuario esta activo pero la sesion se caduco o revoco
            self.__sesion_servicio.limpiar()
            return None
        
        if not sesion.usuario.activo:
            self.cerrar_sesion(sesion)
            return None
        
        return sesion

    def estado_sesion(self)->None:
        '''NO IMPLEMENTADA:

        @return callable | function | lambda

        Esta funcion podria revisar la sesion y retornar un lambda que siempre se ejecuta.
        
        Esto podria usarse para cada peticion que haga el controlador
        y podria usarse para verificar si se revoco la sesion cuando esta la app abierta
        para que en esos casos se cierre y elimine del dispositivo.
        '''
        ...

    def cerrar_sesion(self, sesion: Sesion | None = None) -> bool:
        """Cierra la sesión y borra todo rastro de ella en esta máquina."""
        _sesion:Sesion|None = sesion

        if sesion is None:
            token_guardado = self.__sesion_servicio.cargar()
            if token_guardado is not None:
                _sesion = self.__sesion_repo.obtener_activa(token_guardado)

        if _sesion is not None:
            self.__sesion_repo.revocar(_sesion)

        self.__sesion_servicio.limpiar()

        return _sesion is not None

    def cambiar_contrasena(
        self, usuario: Usuario, contrasena_actual: str, contrasena_nueva: str
    ) -> Usuario:
        """Reemplaza el hash del usuario, exigiendo primero la contraseña vigente."""
        if not self.verificar(contrasena_actual, usuario.hash_contrasena):
            raise ValueError("La contraseña actual no es correcta.")

        usuario.hash_contrasena = self.hashear(contrasena_nueva)
        self.__usuario_repo.guardar(usuario)
        return usuario

    
