"""Controlador de la pantalla de pacientes.

Recibe el repositorio YA CONSTRUIDO (inyección de dependencias): no sabe si
por detrás hay SQLite, memoria o Supabase, y no le importa.
"""

from app.modelos.repositorios import RepositorioPacientes
from app.vistas.ventana_pacientes import VentanaPacientes


class ControladorPacientes:

    def __init__(self, repositorio: RepositorioPacientes):
        self.repositorio = repositorio
        self.vista = VentanaPacientes()

        self.vista.busqueda_cambiada.connect(self.buscar)
        self.vista.alta_solicitada.connect(self.alta)
        self.vista.baja_solicitada.connect(self.baja)

    def buscar(self, texto: str) -> None:
        self.vista.pintar(self.repositorio.listar(texto))

    def alta(self, nombre: str, apellido: str) -> None:
        if not nombre or not apellido:
            self.vista.avisar("Escribe nombre y apellido.")
            return
        try:
            self.repositorio.crear(nombre, apellido)
        except Exception as error:
            self.vista.avisar(f"No se pudo guardar: {error}")
            return
        self.vista.limpiar_formulario()
        self.buscar(self.vista.texto_busqueda())

    def baja(self, paciente_id: int) -> None:
        self.repositorio.eliminar(paciente_id)
        self.buscar(self.vista.texto_busqueda())

    def mostrar(self) -> None:
        # Se recarga en cada apertura. Es una de las dos respuestas posibles
        # a la pregunta que te dejé; ver LEEME.md.
        self.buscar(self.vista.texto_busqueda())
        self.vista.show()
        self.vista.raise_()
        self.vista.activateWindow()
