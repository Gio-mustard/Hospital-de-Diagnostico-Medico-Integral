from app.modelos.repositorios import RepositorioMedicos
from app.vistas.ventana_medicos import VentanaMedicos


class ControladorMedicos:

    def __init__(self, repositorio: RepositorioMedicos):
        self.repositorio = repositorio
        self.vista = VentanaMedicos()

    def mostrar(self) -> None:
        self.vista.pintar(self.repositorio.listar())
        self.vista.show()
        self.vista.raise_()
        self.vista.activateWindow()
