"""Pantalla de pacientes: vista pasiva.

No sabe de dónde salen los datos ni a dónde van. Recibe listas para pintar
y emite señales cuando el usuario hace algo.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


class VentanaPacientes(QWidget):

    busqueda_cambiada = Signal(str)
    alta_solicitada = Signal(str, str)
    baja_solicitada = Signal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pacientes")
        self.resize(520, 380)
        self._ids: list[int] = []

        self.caja_busqueda = QLineEdit(placeholderText="Buscar…")
        self.campo_nombre = QLineEdit(placeholderText="Nombre")
        self.campo_apellido = QLineEdit(placeholderText="Apellido")
        self.boton_agregar = QPushButton("Agregar")
        self.boton_eliminar = QPushButton("Eliminar seleccionado")

        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Apellido"])
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        formulario = QHBoxLayout()
        formulario.addWidget(self.campo_nombre)
        formulario.addWidget(self.campo_apellido)
        formulario.addWidget(self.boton_agregar)

        cuerpo = QVBoxLayout(self)
        cuerpo.addWidget(self.caja_busqueda)
        cuerpo.addWidget(self.tabla)
        cuerpo.addLayout(formulario)
        cuerpo.addWidget(self.boton_eliminar)

        self.caja_busqueda.textChanged.connect(self.busqueda_cambiada)
        self.boton_agregar.clicked.connect(self._pedir_alta)
        self.boton_eliminar.clicked.connect(self._pedir_baja)

    def _pedir_alta(self) -> None:
        self.alta_solicitada.emit(self.campo_nombre.text().strip(),
                                  self.campo_apellido.text().strip())

    def _pedir_baja(self) -> None:
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.baja_solicitada.emit(self._ids[fila])

    def pintar(self, pacientes) -> None:
        self._ids = [p.id for p in pacientes]
        self.tabla.setRowCount(len(pacientes))
        for fila, paciente in enumerate(pacientes):
            self.tabla.setItem(fila, 0, QTableWidgetItem(paciente.nombre))
            self.tabla.setItem(fila, 1, QTableWidgetItem(paciente.apellido))

    def limpiar_formulario(self) -> None:
        self.campo_nombre.clear()
        self.campo_apellido.clear()

    def texto_busqueda(self) -> str:
        return self.caja_busqueda.text().strip()

    def avisar(self, mensaje: str) -> None:
        QMessageBox.warning(self, "Pacientes", mensaje)
