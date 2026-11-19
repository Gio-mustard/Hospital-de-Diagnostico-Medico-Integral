from abc import abstractmethod
import json
from enum import Enum

from model.historial_medico import HistorialMedico
from .repositorio import Repositorio

COLUMNAS = (
    "id_historial",
    "uuid_publico",
    "id_paciente",
    "id_medico",
    "fecha_registro",
    "documento_url",
    "tipo_documento",
    "datos_dinamicos",
    "etiquetas",
)
CLAVE = ("id_historial",)


class HistorialMedicoRepositorio(Repositorio):
    """Contrato del repositorio de historiales medicos.

    Fija sobre un HistorialMedico las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, id_historial: int) -> HistorialMedico | None:
        """Obtiene un historial medico por su ID, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los historiales medicos."""
        ...

    @abstractmethod
    def registrar(self, entidad: HistorialMedico) -> HistorialMedico:
        """Persiste un historial medico nuevo y lo devuelve con su id asignado."""
        ...

    @abstractmethod
    def guardar(self, entidad: HistorialMedico) -> bool:
        """Inserta el historial medico recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: HistorialMedico) -> bool:
        """Da de baja el historial medico recibido."""
        ...


class HistorialMedicoSQLRepository(HistorialMedicoRepositorio):
    """Repositorio de historiales medicos."""

    @staticmethod
    def _a_entidad(row) -> HistorialMedico:
        """Convierte un renglon de la tabla en un HistorialMedico, deserializando el JSON."""
        datos = dict(row)
        if isinstance(datos.get("datos_dinamicos"), str):
            datos["datos_dinamicos"] = json.loads(datos["datos_dinamicos"])
        if isinstance(datos.get("etiquetas"), str):
            datos["etiquetas"] = json.loads(datos["etiquetas"])
        return HistorialMedico(**datos)

    @staticmethod
    def _a_fila(historial: HistorialMedico) -> dict:
        """Convierte un HistorialMedico en columna -> valor listo para SQLite.

        `uuid_publico` se omite cuando viene vacio, para dejar que lo genere el
        DEFAULT de la tabla en el INSERT y para no borrarlo en el UPDATE.
        """
        fila = {
            "id_historial": historial.id_historial,
            "id_paciente": historial.id_paciente,
            "id_medico": historial.id_medico,
            "fecha_registro": (
                historial.fecha_registro.isoformat(sep=" ")
                if hasattr(historial.fecha_registro, "isoformat")
                else str(historial.fecha_registro)
            ),
            "documento_url": historial.documento_url,
            "tipo_documento": (
                historial.tipo_documento.value
                if isinstance(historial.tipo_documento, Enum)
                else historial.tipo_documento
            ),
            "datos_dinamicos": (
                json.dumps(historial.datos_dinamicos, ensure_ascii=False)
                if isinstance(historial.datos_dinamicos, dict)
                else historial.datos_dinamicos
            ),
            "etiquetas": (
                json.dumps(historial.etiquetas, ensure_ascii=False)
                if isinstance(historial.etiquetas, list)
                else historial.etiquetas
            ),
        }
        if historial.uuid_publico is not None:
            fila["uuid_publico"] = historial.uuid_publico
        return fila

    def obtener_por_id(self, id_historial: int) -> HistorialMedico | None:
        """Obtiene un historial medico por su ID."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM HistorialMedico
            WHERE id_historial = ?
        """
        row = self.db.execute(sql, (id_historial,)).fetchone()
        return self._a_entidad(row) if row else None

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los historiales, del mas reciente al mas antiguo."""
        sql = f"""
            SELECT {', '.join(COLUMNAS)}
            FROM HistorialMedico
            ORDER BY fecha_registro DESC, id_historial DESC
        """
        return tuple(self._a_entidad(row) for row in self._filas(sql))

    def registrar(self, entidad: HistorialMedico) -> HistorialMedico:
        """Registra un documento en el historial medico."""
        historial = entidad
        historial._validar_propiedades()
        fila = self._a_fila(historial)

        if historial.uuid_publico is not None:
            sql = """
                INSERT INTO HistorialMedico (
                    uuid_publico, id_paciente, id_medico, fecha_registro,
                    documento_url, tipo_documento, datos_dinamicos, etiquetas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                fila["uuid_publico"],
                fila["id_paciente"],
                fila["id_medico"],
                fila["fecha_registro"],
                fila["documento_url"],
                fila["tipo_documento"],
                fila["datos_dinamicos"],
                fila["etiquetas"],
            )
        else:
            sql = """
                INSERT INTO HistorialMedico (
                    id_paciente, id_medico, fecha_registro,
                    documento_url, tipo_documento, datos_dinamicos, etiquetas
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                fila["id_paciente"],
                fila["id_medico"],
                fila["fecha_registro"],
                fila["documento_url"],
                fila["tipo_documento"],
                fila["datos_dinamicos"],
                fila["etiquetas"],
            )

        cursor = self.db.execute(sql, params)
        historial.id_historial = cursor.lastrowid
        return historial

    def guardar(self, entidad: HistorialMedico) -> bool:
        """Inserta el historial o actualiza el existente (upsert por id_historial)."""
        historial = entidad
        historial._validar_propiedades()
        cursor = self._upsert("HistorialMedico", self._a_fila(historial), CLAVE)
        if historial.id_historial is None:
            historial.id_historial = cursor.lastrowid
        return cursor.rowcount > 0

    def darbaja(self, entidad: HistorialMedico) -> bool:
        """Elimina el registro de historial medico recibido."""
        historial = entidad
        if historial.id_historial is None:
            return False
        sql = "DELETE FROM HistorialMedico WHERE id_historial = ?"
        cursor = self.db.execute(sql, (historial.id_historial,))
        return cursor.rowcount > 0
