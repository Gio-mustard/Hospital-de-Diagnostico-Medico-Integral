from abc import abstractmethod
from enum import Enum
from datetime import date
from model.derechohabiente import DerechoHabiente
from .repositorio import Repositorio

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
COLUMNAS_SIN_CLAVE = COLUMNAS[1:]
CLAVE = ("id_derechohabiente",)


class DerechoHabienteRepositorio(Repositorio):
    """Contrato del repositorio de derechohabientes.

    Fija sobre un DerechoHabiente las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_derechohabiente: int) -> DerechoHabiente | None:
        """Obtiene un derechohabiente por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los derechohabientes."""
        ...

    @abstractmethod
    def registrar(self, entidad: DerechoHabiente) -> DerechoHabiente:
        """Persiste un derechohabiente nuevo y lo devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: DerechoHabiente) -> bool:
        """Inserta el derechohabiente recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: DerechoHabiente) -> bool:
        """Da de baja el derechohabiente recibido."""
        ...


class DerechoHabienteSQLRepository(DerechoHabienteRepositorio):
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
                if hasattr(dh.fecha_nacimiento, "isoformat") and isinstance(dh.fecha_nacimiento,date)
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

    def registrar(self, entidad: DerechoHabiente) -> DerechoHabiente:
        """Inserta un nuevo derechohabiente y asigna su id_derechohabiente."""
        dh = entidad
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

    def guardar(self, entidad: DerechoHabiente) -> bool:
        """Inserta el derechohabiente o actualiza el existente (upsert por id)."""
        dh = entidad
        dh._validar_propiedades()
        cursor = self._upsert("DerechoHabiente", self._a_fila(dh), CLAVE)
        if dh.id_derechohabiente is None:
            dh.id_derechohabiente = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, entidad: DerechoHabiente) -> bool:
        """Da de baja logica (activo = 0) al derechohabiente recibido."""
        dh = entidad
        if dh.id_derechohabiente is None:
            return False
        sql = "UPDATE DerechoHabiente SET activo = 0 WHERE id_derechohabiente = ?"
        cursor = self.db.execute(sql, (dh.id_derechohabiente,))
        if cursor.rowcount > 0:
            dh.activo = False
            return True
        return False
