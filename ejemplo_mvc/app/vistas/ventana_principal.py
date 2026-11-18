"""Menú principal.

Fíjate en lo que NO hay aquí: ni un import de controladores, ni de modelos,
ni de las otras ventanas. Solo grita el nombre de la pantalla que quieren.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget


class VentanaPrincipal(QMainWindow):

    pantalla_solicitada = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hospital — menú")
        self.resize(320, 160)

        boton_pacientes = QPushButton("Pacientes")
        boton_medicos = QPushButton("Médicos")
        boton_pacientes.clicked.connect(lambda: self.pantalla_solicitada.emit("pacientes"))
        boton_medicos.clicked.connect(lambda: self.pantalla_solicitada.emit("medicos"))

        cuerpo = QVBoxLayout()
        cuerpo.addWidget(boton_pacientes)
        cuerpo.addWidget(boton_medicos)
        central = QWidget()
        central.setLayout(cuerpo)
        self.setCentralWidget(central)
