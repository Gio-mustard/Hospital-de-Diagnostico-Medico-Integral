"""Modelos del Hospital de Diagnóstico Médico Integral.

Una clase por tabla de `ddl.sql`, más tres clases abstractas que concentran lo
que varias tablas repiten:

    Entidad (abstracta, en constants.py)
    ├── DerechoHabiente
    │   ├── Paciente
    │   ├── Recepcionista
    │   └── Trabajador
    │       ├── Medico
    │       └── Enfermero
    ├── Especialidad
    ├── AsignacionEspecialidad (abstracta)
    │   ├── MedicoEspecialidad
    │   └── EnfermeroEspecialidad
    ├── EspacioFisico (abstracta)
    │   ├── Habitacion
    │   └── Consultorio
    ├── Medicamento
    ├── HistorialMedico
    ├── AtencionMedica (abstracta)
    │   ├── Cita
    │   └── IngresoEmergencia
    ├── Ingreso
    ├── Receta
    └── DetalleReceta

Las tablas `AuditoriaClinica` y la vista `vista_citas_recepcion` aparecen en los
DROP del DDL pero nunca se crean, así que no tienen modelo.
"""

from .asignacion_especialidad import (
    AsignacionEspecialidad,
    EnfermeroEspecialidad,
    MedicoEspecialidad,
)
from .atencion_medica import AtencionMedica
from .cita import Cita
from .constants import (
    CLAVES_TRATAMIENTO,
    DIAS_MINIMOS_CADUCIDAD,
    Entidad,
    EstadosCita,
    EstadosConsultorio,
    EstadosHabitacion,
    Generos,
    NivelesUrgencia,
    TiposDocumento,
    TiposHabitacion,
    TiposSangre,
    Turnos,
)
from .consultorio import Consultorio
from .derechohabiente import DerechoHabiente
from .detalle_receta import DetalleReceta
from .enfermero import Enfermero
from .espacio_fisico import EspacioFisico
from .especialidad import Especialidad
from .habitacion import Habitacion
from .historial_medico import HistorialMedico
from .ingreso import Ingreso
from .ingreso_emergencia import IngresoEmergencia
from .medicamento import Medicamento
from .medico import Medico
from .paciente import Paciente
from .receta import Receta
from .recepcionista import Recepcionista
from .trabajador import Trabajador

__all__ = [
    # Base y enumeraciones
    'Entidad',
    'Generos',
    'TiposSangre',
    'Turnos',
    'TiposHabitacion',
    'EstadosHabitacion',
    'EstadosConsultorio',
    'TiposDocumento',
    'EstadosCita',
    'NivelesUrgencia',
    'CLAVES_TRATAMIENTO',
    'DIAS_MINIMOS_CADUCIDAD',
    # Personas
    'DerechoHabiente',
    'Paciente',
    'Trabajador',
    'Medico',
    'Enfermero',
    'Recepcionista',
    # Especialidades
    'Especialidad',
    'AsignacionEspecialidad',
    'MedicoEspecialidad',
    'EnfermeroEspecialidad',
    # Espacios
    'EspacioFisico',
    'Habitacion',
    'Consultorio',
    # Clínico
    'Medicamento',
    'HistorialMedico',
    'AtencionMedica',
    'Cita',
    'IngresoEmergencia',
    'Ingreso',
    'Receta',
    'DetalleReceta',
]
