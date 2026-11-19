from abc import abstractmethod

from model.espacio_fisico import EspacioFisico
from model.habitacion import Habitacion
from model.consultorio import Consultorio
from .repositorio import Repositorio
from .habitacion import HabitacionSQLRepository
from .consultorio import ConsultorioSQLRepository


class EspacioFisicoRepositorio(Repositorio):
    """Contrato del repositorio de espacios fisicos.

    Fija sobre un EspacioFisico las firmas que Repositorio declara en abstracto,
    para que el resto del sistema dependa de esta interfaz y no de una
    implementacion concreta: cualquier almacenamiento que la cumpla (SQL, en
    memoria, un doble de prueba) es intercambiable sin tocar a quien la usa.
    """

    @abstractmethod
    def obtener_por_id(self, numero: int, es_consultorio: bool = False) -> Habitacion | Consultorio | None:
        """Obtiene un espacio fisico por su numero, o None si no existe."""
        ...

    @abstractmethod
    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los espacios fisicos."""
        ...

    @abstractmethod
    def registrar(self, entidad: EspacioFisico) -> EspacioFisico:
        """Persiste un espacio fisico nuevo y lo devuelve."""
        ...

    @abstractmethod
    def guardar(self, entidad: EspacioFisico) -> bool:
        """Inserta el espacio fisico recibido o actualiza el que ya existe."""
        ...

    @abstractmethod
    def darbaja(self, entidad: EspacioFisico) -> bool:
        """Da de baja el espacio fisico recibido."""
        ...


class EspacioFisicoSQLRepository(EspacioFisicoRepositorio):
    """Repositorio fachada para Habitacion y Consultorio."""

    @property
    def _hab_repo(self) -> HabitacionSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return HabitacionSQLRepository(self.db)

    @property
    def _cons_repo(self) -> ConsultorioSQLRepository:
        """Repositorio colaborador, montado sobre la misma base de datos."""
        return ConsultorioSQLRepository(self.db)

    def _repo_de(self, espacio: EspacioFisico) -> Repositorio:
        """Devuelve el repositorio concreto que le toca a la entidad recibida."""
        if isinstance(espacio, Habitacion):
            return self._hab_repo
        if isinstance(espacio, Consultorio):
            return self._cons_repo
        raise TypeError("Se esperaba una instancia de Habitacion o Consultorio.")

    def obtener_por_id(
        self, numero: int, es_consultorio: bool = False
    ) -> Habitacion | Consultorio | None:
        """Obtiene una Habitacion o Consultorio por su numero."""
        if es_consultorio:
            return self._cons_repo.obtener_por_id(numero)
        return self._hab_repo.obtener_por_id(numero)

    def obtener_todos(self) -> tuple:
        """Retorna la tupla con todos los espacios: primero habitaciones, luego consultorios."""
        return self._hab_repo.obtener_todos() + self._cons_repo.obtener_todos()

    def registrar(self, entidad: EspacioFisico) -> EspacioFisico:
        """Registra una Habitacion o un Consultorio."""
        espacio = entidad
        return self._repo_de(espacio).registrar(espacio)

    def guardar(self, entidad: EspacioFisico) -> bool:
        """Hace upsert de la Habitacion o del Consultorio recibido."""
        espacio = entidad
        return self._repo_de(espacio).guardar(espacio)

    def darbaja(self, entidad: EspacioFisico) -> bool:
        """Da de baja la Habitacion o el Consultorio recibido."""
        espacio = entidad
        return self._repo_de(espacio).darbaja(espacio)
