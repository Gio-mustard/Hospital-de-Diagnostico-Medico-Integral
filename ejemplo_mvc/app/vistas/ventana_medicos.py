"""Pantalla de médicos: solo lista. Sirve para ver que el coordinador
maneja dos pantallas y que no todas necesitan el mismo trabajo."""

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget


class VentanaMedicos(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Médicos")
        self.resize(380, 260)
        self.lista = QListWidget()
        cuerpo = QVBoxLayout(self)
        cuerpo.addWidget(self.lista)

    def pintar(self, medicos) -> None:
        self.lista.clear()
        for medico in medicos:
            self.lista.addItem(f"{medico.nombre} — {medico.especialidad}")
