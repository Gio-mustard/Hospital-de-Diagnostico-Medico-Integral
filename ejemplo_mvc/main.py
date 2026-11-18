"""Raíz de composición: el ÚNICO archivo que decide qué implementación se usa.

Para correr sin base de datos, cambia las dos líneas marcadas por sus
versiones de memoria. Nada más en toda la app se entera del cambio.

    ../env/bin/python main.py
"""

import sys

from PySide6.QtWidgets import QApplication

from app.controladores.coordinador import Coordinador
from app.modelos.repositorios_sqlite import (RepositorioMedicosSQLite,
                                             RepositorioPacientesSQLite)
# from app.modelos.repositorios_memoria import (RepositorioMedicosMemoria,
#                                               RepositorioPacientesMemoria)


def main() -> int:
    aplicacion = QApplication(sys.argv)

    repositorios = {
        "pacientes": RepositorioPacientesSQLite(),   # <- cámbiame
        "medicos": RepositorioMedicosSQLite(),       # <- cámbiame
    }

    coordinador = Coordinador(repositorios)
    coordinador.iniciar()
    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())
