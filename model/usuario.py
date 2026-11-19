"""Tabla de usuarios del sistema. Contiene los datos de los usuarios que pueden iniciar sesión en el sistema y sus roles."""


from .constants import LONGITUD_UUID, Entidad, Roles

class Usuario(Entidad):
    """Representa un usuario del sistema con sus credenciales y roles.

    `activo` es la baja lógica de la credencial, igual que en DerechoHabiente y
    sus hijas: desactivar un usuario le quita el acceso sin borrar la fila. Y
    borrarla no sería opción de todos modos, porque `DerechoHabiente` apunta
    aquí con un `ON DELETE RESTRICT`: un usuario ligado a una persona no se
    puede eliminar. Quién hace valer la bandera al entrar al sistema es `Auth`,
    no el repositorio.
    """

    _CAMPOS_CLAVE = ('id',)
    def __init__(
        self,
        *,
        id: str,
        hash_contrasena: str,
        correo: str,
        rol: Roles,
        activo: bool = True,
    ) -> None:
        self.id = id
        self.hash_contrasena = hash_contrasena
        self.correo = correo
        self.rol = rol
        self.activo = activo

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Usuario:
            self._validar_propiedades()

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()

        self._validar_texto('id', LONGITUD_UUID)
        if len(self.id) != LONGITUD_UUID:
            self._fallar(
                'id', self.id, f"debe medir exactamente {LONGITUD_UUID} caracteres"
            )

        self._validar_texto('hash_contrasena', 255)
        self._validar_patron('correo', r'^[^@]+@[^@]+\.[^@]+$', 'correo electrónico')
        self._validar_enum('rol',Roles)
        self._validar_booleano('activo')
