from .repositorio import Repositorio
from .asignacion_especialidad import AsignacionEspecialidadSQLRepository
from .atencion_medica import AtencionMedicaSQLRepository
from .cita import CitaSQLRepository
from .consultorio import ConsultorioSQLRepository
from .derechohabiente import DerechoHabienteSQLRepository
from .detalle_receta import DetalleRecetaSQLRepository
from .enfermero import EnfermeroSQLRepository
from .espacio_fisico import EspacioFisicoSQLRepository
from .especialidad import EspecialidadSQLRepository
from .habitacion import HabitacionSQLRepository
from .historial_medico import HistorialMedicoSQLRepository
from .ingreso_emergencia import IngresoEmergenciaSQLRepository
from .ingreso import IngresoSQLRepository
from .medicamento import MedicamentoSQLRepository
from .medico import MedicoSQLRepository
from .paciente import PacienteSQLRepository
from .recepcionista import RecepcionistaSQLRepository
from .receta import RecetaSQLRepository
from .trabajador import TrabajadorSQLRepository
from .usuario import UsuarioSQLRepository

__all__ = [
    "Repositorio",
    "AsignacionEspecialidadSQLRepository",
    "AtencionMedicaSQLRepository",
    "CitaSQLRepository",
    "ConsultorioSQLRepository",
    "DerechoHabienteSQLRepository",
    "DetalleRecetaSQLRepository",
    "EnfermeroSQLRepository",
    "EspacioFisicoSQLRepository",
    "EspecialidadSQLRepository",
    "HabitacionSQLRepository",
    "HistorialMedicoSQLRepository",
    "IngresoEmergenciaSQLRepository",
    "IngresoSQLRepository",
    "MedicamentoSQLRepository",
    "MedicoSQLRepository",
    "PacienteSQLRepository",
    "RecepcionistaSQLRepository",
    "RecetaSQLRepository",
    "TrabajadorSQLRepository",
    "UsuarioSQLRepository",
]
