"""Tabla de usuarios del sistema. Contiene los datos de los usuarios que pueden iniciar sesión en el sistema y sus roles."""


from .constants import LONGITUD_UUID, Entidad, Roles

class Usuario(Entidad):
    """Representa un usuario del sistema con sus credenciales y roles."""

    _CAMPOS_CLAVE = ('id',)
    def __init__(
        self,
        *,
        id: str,
        hash_contrasena: str,
        correo: str,
        rol: str,
    ) -> None:
        self.id = id
        self.hash_contrasena = hash_contrasena
        self.correo = correo
        self.rol = rol

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()

        # id TEXT PRIMARY KEY: es un UUID que trae quien crea el usuario, no un
        # AUTOINCREMENT, asi que se valida como texto de 36 caracteres y no con
        # _validar_clave_propia, que exige un entero >= 1 y rechazaba todo UUID.
        self._validar_texto('id', LONGITUD_UUID)
        if len(self.id) != LONGITUD_UUID:
            self._fallar(
                'id', self.id, f"debe medir exactamente {LONGITUD_UUID} caracteres"
            )

        self._validar_texto('hash_contrasena', 255)
        self._validar_patron('correo', r'^[^@]+@[^@]+\.[^@]+$', 'correo electrónico')
        self._validar_enum('rol',Roles)