from enum import Enum

from model.usuario import Usuario
from .repositorio import Repositorio

COLUMNAS = ("id", "hash_contrasena", "correo", "rol")
CLAVE = ("id",)


class UsuarioSQLRepository(Repositorio):
    """Repositorio de usuarios del sistema."""

    @staticmethod
    def _a_entidad(row) -> Usuario:
        """Convierte un renglon de la tabla en un Usuario."""
        return Usuario(**dict(row))

    @staticmethod
    def _a_fila(usuario: Usuario) -> dict:
        """Convierte un Usuario en columna -> valor listo para SQLite."""
        return {
            "id": usuario.id,
            "hash_contrasena": usuario.hash_contrasena,
            "correo": usuario.correo,
            "rol": usuario.rol.value if isinstance(usuario.rol, Enum) else usuario.rol,
        }

    def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        """Obtiene un usuario por su UUID/ID."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Usuario WHERE id = ?"
        row = self.db.execute(sql, (id_usuario,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los usuarios, ordenados por id."""
        sql = f"SELECT {', '.join(COLUMNAS)} FROM Usuario ORDER BY id"
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, usuario: Usuario) -> Usuario:
        """Registra un nuevo usuario en el sistema."""
        usuario._validar_propiedades()
        rol_val = usuario.rol.value if isinstance(usuario.rol, Enum) else usuario.rol
        sql = """
            INSERT INTO Usuario (id, hash_contrasena, correo, rol)
            VALUES (?, ?, ?, ?)
        """
        self.db.execute(
            sql, (usuario.id, usuario.hash_contrasena, usuario.correo, rol_val)
        )
        return usuario

    def guardar(self, usuario: Usuario) -> bool:
        """Inserta el usuario o actualiza el existente (upsert por id)."""
        usuario._validar_propiedades()
        cursor = self._upsert("Usuario", self._a_fila(usuario), CLAVE)
        return cursor.rowcount > 0

    def darbaja(self, usuario: Usuario) -> bool:
        """Elimina del sistema al usuario recibido."""
        if usuario.id is None:
            return False
        sql = "DELETE FROM Usuario WHERE id = ?"
        cursor = self.db.execute(sql, (usuario.id,))
        return cursor.rowcount > 0
