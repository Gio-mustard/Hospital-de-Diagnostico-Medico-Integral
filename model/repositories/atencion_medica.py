from model.atencion_medica import AtencionMedica
from model.cita import Cita
from model.ingreso_emergencia import IngresoEmergencia
from .repositorio import Repositorio
from .cita import CitaSQLRepository
from .ingreso_emergencia import IngresoEmergenciaSQLRepository


class AtencionMedicaSQLRepository(Repositorio):
    """Repositorio fachada para las especializaciones de AtencionMedica (Cita e IngresoEmergencia)."""

    @property
    def _cita_repo(self) -> CitaSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return CitaSQLRepository(self.db)

    @property
    def _emergencia_repo(self) -> IngresoEmergenciaSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return IngresoEmergenciaSQLRepository(self.db)

    def _repo_de(self, atencion: AtencionMedica) -> Repositorio:
        """Devuelve el repositorio concreto que le toca a la entidad recibida."""
        if isinstance(atencion, Cita):
            return self._cita_repo
        if isinstance(atencion, IngresoEmergencia):
            return self._emergencia_repo
        raise TypeError("La atencion medica debe ser una instancia de Cita o IngresoEmergencia.")

    def obtener_por_id(
        self, id_atencion: int, es_emergencia: bool = False
    ) -> Cita | IngresoEmergencia | None:
        """Obtiene una Cita o un IngresoEmergencia por su ID."""
        if es_emergencia:
            return self._emergencia_repo.obtener_por_id(id_atencion)
        return self._cita_repo.obtener_por_id(id_atencion)

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todas las atenciones: primero las citas, luego las emergencias."""
        return self._cita_repo.obtener_todos() + self._emergencia_repo.obtener_todos()

    def registrar(self, atencion: AtencionMedica) -> AtencionMedica:
        """Registra una Cita o un IngresoEmergencia segun el tipo recibido."""
        return self._repo_de(atencion).registrar(atencion)

    def guardar(self, atencion: AtencionMedica) -> bool:
        """Hace upsert de la Cita o del IngresoEmergencia recibido."""
        return self._repo_de(atencion).guardar(atencion)

    def darbaja(self, atencion: AtencionMedica) -> bool:
        """Da de baja la Cita o el IngresoEmergencia recibido."""
        return self._repo_de(atencion).darbaja(atencion)
