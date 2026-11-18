
from model.database import Database
from model.derechohabiente import DerechoHabiente


class DerechoHabienteRepository:
    """Repositorio de derechohabientes."""

    def __init__(self, db: Database):
        self._db = db


    def obtener_por_id(self, id_derechohabiente: int) -> DerechoHabiente | None:
        """Obtiene un derechohabiente por su ID."""
        sql = "SELECT * FROM derechohabiente WHERE id_derechohabiente = ?"
        row = self._db.execute('select * from derechohabiente where id_derechohabiente = ?', (id_derechohabiente,)).fetchone()

    def registrar():
        pass


    def darbaja():
        pass