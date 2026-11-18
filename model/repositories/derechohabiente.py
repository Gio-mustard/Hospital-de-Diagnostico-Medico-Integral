from enum import Enum

from model.derechohabiente import DerechoHabiente
from .repositorio import Repositorio

#: Columnas de la tabla DerechoHabiente.
COLUMNAS = (
    "id_derechohabiente",
    "auth_user_id",
    "nombres",
    "apellido_paterno",
    "apellido_materno",
    "direccion_calle",
    "codigo_postal",
    "ciudad",
    "estado",
    "fecha_nacimiento",
    "genero",
    "telefono",
    "curp",
    "activo",
)
#: Las mismas columnas sin la llave primaria, para los JOIN de las tablas hijas
#: que ya traen su propio `id_derechohabiente`.
COLUMNAS_SIN_CLAVE = COLUMNAS[1:]
#: Llave primaria AUTOINCREMENT.
CLAVE = ("id_derechohabiente",)


class DerechoHabienteSQLRepository(Repositorio):
    """Repositorio de derechohabientes."""

    @staticmethod
    def _a_entidad(row) -> DerechoHabiente:
        """Convierte un renglon de la tabla en un DerechoHabiente."""
        datos = dict(row)
        datos["activo"] = bool(datos["activo"])
        return DerechoHabiente(**datos)

    @staticmethod
    def _a_fila(dh: DerechoHabiente) -> dict:
        """Convierte un DerechoHabiente en columna -> valor listo para SQLite."""
        return {
            "id_derechohabiente": dh.id_derechohabiente,
            "auth_user_id": dh.auth_user_id,
            "nombres": dh.nombres,
            "apellido_paterno": dh.apellido_paterno,
            "apellido_materno": dh.apellido_materno,
            "direccion_calle": dh.direccion_calle,
            "codigo_postal": dh.codigo_postal,
            "ciudad": dh.ciudad,
            "estado": dh.estado,
            "fecha_nacimiento": (
                dh.fecha_nacimiento.isoformat()
                if hasattr(dh.fecha_nacimiento, "isoformat")
                else str(dh.fecha_nacimiento)
            ),
            "genero": dh.genero.value if isinstance(dh.genero, Enum) else dh.genero,
            "telefono": dh.telefono,
            "curp": dh.curp,
            "activo": int(bool(dh.activo)),
        }

    def obtener_por_id(self, id_derechohabiente: int) -> DerechoHabiente | None:
        """Obtiene un derechohabiente por su ID."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM DerechoHabiente
            WHERE id_derechohabiente = ?
        """
        row = self.db.execute(sql, (id_derechohabiente,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los derechohabientes, ordenados por nombre."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM DerechoHabiente
            ORDER BY apellido_paterno, apellido_materno, nombres
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, dh: DerechoHabiente) -> DerechoHabiente:
        """Inserta un nuevo derechohabiente y asigna su id_derechohabiente."""
        dh._validar_propiedades()
        fila = self._a_fila(dh)

        sql = """
            INSERT INTO DerechoHabiente (
                auth_user_id, nombres, apellido_paterno, apellido_materno,
                direccion_calle, codigo_postal, ciudad, estado,
                fecha_nacimiento, genero, telefono, curp, activo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.db.execute(
            sql, tuple(fila[col] for col in COLUMNAS_SIN_CLAVE)
        )
        dh.id_derechohabiente = cursor.lastrowid
        return dh

    def guardar(self, dh: DerechoHabiente) -> bool:
        """Inserta el derechohabiente o actualiza el existente (upsert por id)."""
        dh._validar_propiedades()
        cursor = self._upsert("DerechoHabiente", self._a_fila(dh), CLAVE)
        if dh.id_derechohabiente is None:
            dh.id_derechohabiente = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, dh: DerechoHabiente) -> bool:
        """Da de baja logica (activo = 0) al derechohabiente recibido."""
        if dh.id_derechohabiente is None:
            return False
        sql = "UPDATE DerechoHabiente SET activo = 0 WHERE id_derechohabiente = ?"
        cursor = self.db.execute(sql, (dh.id_derechohabiente,))
        if cursor.rowcount > 0:
            dh.activo = False
            return True
        return False
