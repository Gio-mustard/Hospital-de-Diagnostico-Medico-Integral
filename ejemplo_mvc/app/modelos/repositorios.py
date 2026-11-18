"""Las INTERFACES. El controlador solo conoce esto, nunca una implementación.

Gracias a estas dos clases abstractas, cambiar SQLite por Supabase no toca
ni una línea de los controladores ni de las vistas.
"""

from abc import ABC, abstractmethod

from app.modelos.entidades import Medico, Paciente


class RepositorioPacientes(ABC):

    @abstractmethod
    def listar(self, busqueda: str = "") -> list[Paciente]: ...

    @abstractmethod
    def crear(self, nombre: str, apellido: str) -> int: ...

    @abstractmethod
    def eliminar(self, paciente_id: int) -> int: ...


class RepositorioMedicos(ABC):

    @abstractmethod
    def listar(self) -> list[Medico]: ...
