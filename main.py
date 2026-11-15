import sys
from PySide6.QtWidgets import QApplication, QMainWindow

aplicacion = QApplication(sys.argv)
ventana = QMainWindow()
ventana.show()           
sys.exit(aplicacion.exec())