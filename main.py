import sys
from PySide6.QtWidgets import QApplication, QMainWindow

from model.database import Database
from model.derechohabienteRepository import DerechoHabienteRepository

aplicacion = QApplication(sys.argv)

database = Database("hospital.db")


database.connect()


ventana = QMainWindow()


ventana.show()           
sys.exit(aplicacion.exec())