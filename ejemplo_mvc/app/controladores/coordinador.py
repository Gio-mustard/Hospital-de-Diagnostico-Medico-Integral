"""La pieza que faltaba: el único objeto que conoce el mapa de la app.

Hace dos cosas:
  1. Crea cada controlador la primera vez que alguien pide su pantalla
     (creación bajo demanda, no al arrancar).
  2. Lo guarda en self.vivos, que es la referencia de Python que evita que
     el recolector de basura se lleve el controlador y mate su ventana.
"""

from app.controladores.controlador_medicos import ControladorMedicos
from app.controladores.controlador_pacientes import ControladorPacientes
from app.vistas.ventana_principal import VentanaPrincipal


class Coordinador:

    def __init__(self, repositorios: dict):
        self.vivos: dict[str, object] = {}
        self.fabricas = {
            "pacientes": lambda: ControladorPacientes(repositorios["pacientes"]),
            "medicos": lambda: ControladorMedicos(repositorios["medicos"]),
        }
        self.principal = VentanaPrincipal()
        self.principal.pantalla_solicitada.connect(self.abrir)

    def abrir(self, clave: str) -> None:
        if clave not in self.vivos:
            self.vivos[clave] = self.fabricas[clave]()
        self.vivos[clave].mostrar()

    def iniciar(self) -> None:
        self.principal.show()
