"""Repositorios del sistema.

Cada entidad expone dos nombres: la interfaz abstracta (`XRepositorio`), que es
el contrato contra el que programa el resto del sistema, y la implementacion
sobre SQLite (`XSQLRepository`), que es la que se inyecta en tiempo de
ejecucion. Depender de la interfaz es lo que permite cambiar el almacenamiento
o inyectar un doble de prueba sin tocar a quien la consume.
"""

from .repositorio import Repositorio

from .asignacion_especialidad import (
    AsignacionEspecialidadRepositorio,
    AsignacionEspecialidadSQLRepository,
)
from .atencion_medica import AtencionMedicaRepositorio, AtencionMedicaSQLRepository
from .cita import CitaRepositorio, CitaSQLRepository
from .consultorio import ConsultorioRepositorio, ConsultorioSQLRepository
from .derechohabiente import DerechoHabienteRepositorio, DerechoHabienteSQLRepository
from .detalle_receta import DetalleRecetaRepositorio, DetalleRecetaSQLRepository
from .enfermero import EnfermeroRepositorio, EnfermeroSQLRepository
from .espacio_fisico import EspacioFisicoRepositorio, EspacioFisicoSQLRepository
from .especialidad import EspecialidadRepositorio, EspecialidadSQLRepository
from .habitacion import HabitacionRepositorio, HabitacionSQLRepository
from .historial_medico import HistorialMedicoRepositorio, HistorialMedicoSQLRepository
from .ingreso_emergencia import (
    IngresoEmergenciaRepositorio,
    IngresoEmergenciaSQLRepository,
)
from .ingreso import IngresoRepositorio, IngresoSQLRepository
from .medicamento import MedicamentoRepositorio, MedicamentoSQLRepository
from .medico import MedicoRepositorio, MedicoSQLRepository
from .paciente import PacienteRepositorio, PacienteSQLRepository
from .recepcionista import RecepcionistaRepositorio, RecepcionistaSQLRepository
from .receta import RecetaRepositorio, RecetaSQLRepository
from .trabajador import TrabajadorRepositorio, TrabajadorSQLRepository
from .usuario import UsuarioRepositorio, UsuarioSQLRepository

__all__ = [
    "Repositorio",
    # Interfaces
    "AsignacionEspecialidadRepositorio",
    "AtencionMedicaRepositorio",
    "CitaRepositorio",
    "ConsultorioRepositorio",
    "DerechoHabienteRepositorio",
    "DetalleRecetaRepositorio",
    "EnfermeroRepositorio",
    "EspacioFisicoRepositorio",
    "EspecialidadRepositorio",
    "HabitacionRepositorio",
    "HistorialMedicoRepositorio",
    "IngresoEmergenciaRepositorio",
    "IngresoRepositorio",
    "MedicamentoRepositorio",
    "MedicoRepositorio",
    "PacienteRepositorio",
    "RecepcionistaRepositorio",
    "RecetaRepositorio",
    "TrabajadorRepositorio",
    "UsuarioRepositorio",
    # Implementaciones SQL
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
