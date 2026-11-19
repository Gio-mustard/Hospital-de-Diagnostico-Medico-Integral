from abc import abstractmethod
from enum import Enum

from model.usuario import Usuario
from .repositorio import Repositorio

COLUMNAS = ("id", "hash_contrasena", "correo", "rol", "activo")
CLAVE = ("id",)


class UsuarioRepositorio(Repositorio):
    """Contrato del repositorio de usuarios.

    Fija sobre un Usuario las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.

    Agrega `obtener_por_correo`, que no esta en el contrato comun pero si lo
    necesita la autenticacion: el correo es la credencial con la que se ingresa
    al sistema, no la llave primaria.
    """

    @abstractmethod
    def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        """Obtiene un usuario por su UUID/ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_por_correo(self, correo: str) -> Usuario | None:
        """Obtiene un usuario por su correo, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los usuarios."""
        ...

    @abstractmethod
    def registrar(self, entidad: Usuario) -> Usuario:
        """Persiste un usuario nuevo y lo devuelve."""
        ...

    @abstractmethod
    def guardar(self, entidad: Usuario) -> bool:
        """Inserta el usuario recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: Usuario) -> bool:
        """Da de baja el usuario recibido, quitandole el acceso al sistema.

        Es baja logica: la fila se queda y solo pasa `activo` a 0. Hacer valer
        la bandera al iniciar sesion le toca a `Auth`, no al repositorio.
        """
        ...


class UsuarioSQLRepository(UsuarioRepositorio):
    """Repositorio de usuarios del sistema."""

    @staticmethod
    def _a_entidad(row) -> Usuario:
        """Convierte un renglon de la tabla en un Usuario."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return Usuario(**datos)

    @staticmethod
    def _a_fila(usuario: Usuario) -> dict:
        """Convierte un Usuario en columna -> valor listo para SQLite."""
        return {
            "id": usuario.id,
            "hash_contrasena": usuario.hash_contrasena,
            "correo": usuario.correo,
            "rol": usuario.rol.value if isinstance(usuario.rol, Enum) else usuario.rol,
            "activo": int(bool(usuario.activo)),
        }

    def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        """Obtiene un usuario por su UUID/ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Usuario WHERE id = ?"
        row = self.db.execute(sql, (id_usuario,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        """Obtiene un usuario por su UUID/ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Usuario WHERE correo = ?"
        row = self.db.execute(sql, (correo,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los usuarios, ordenados por id."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Usuario ORDER BY id"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: Usuario) -> Usuario:
        """Registra un nuevo usuario en el sistema."""
        usuario = entidad
        usuario._validar_propiedades()
        fila = self._a_fila(usuario)
        sql = """
            INSERT INTO Usuario (id, hash_contrasena, correo, rol, activo)
            VALUES (?, ?, ?, ?, ?)
        """
        self.db.execute(sql, tuple(fila[col] for col in COLUMNAS))
        return usuario

    def guardar(self, entidad: Usuario) -> bool:
        """Inserta el usuario o actualiza el existente (upsert por id)."""
        usuario = entidad
        usuario._validar_propiedades()
        cursor = self._upsert("Usuario", self._a_fila(usuario), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, entidad: Usuario) -> bool:
        """Da de baja logica al usuario recibido (activo = 0).

        No es un DELETE: `DerechoHabiente.auth_user_id` apunta aqui con
        ON DELETE RESTRICT, asi que borrar la fila de un usuario que ya esta
        ligado a una persona es imposible. Desactivarlo si se puede siempre, y
        es lo coherente con el resto del sistema, donde todas las bajas de
        personas son logicas.
        """
        usuario = entidad
        if usuario.id is None:
            return False
        sql = "UPDATE Usuario SET activo = 0 WHERE id = ?"
        cursor = self.db.execute(sql, (usuario.id,))
        if cursor.rowcount > 0:
            usuario.activo = False
            return True
        return False
