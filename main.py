"""
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
"""
import uuid
from model.trabajador import Trabajador
from model.medico import Medico
from model.usuario import Usuario
from utils.auth import Sesion
from model.constants import Roles


medico_prueba = Medico(
    cedula_profesional='12345678',
    numero_empleado='EMP-0001',
    departamento='Medicina Interna',
    fecha_ingreso='2015-03-01',
    nombres='Ricardo',
    apellido_paterno='González',
    apellido_materno='López',
    direccion_calle='Av. Reforma 123',
    codigo_postal='21100',
    ciudad='Mexicali',
    estado='Baja California',
    fecha_nacimiento='1980-05-15',
    genero='Masculino',
    telefono='+526861234567',
    curp='GOLR800515HBCNPS09',
    activo=True,
    auth_user_id=uuid.uuid4().hex,
    id_derechohabiente=1,
    id_medico=1,
    id_trabajador=1
)

usuario_prueba = Usuario(id=uuid.uuid4().hex,hash_contrasena='uwu',correo="correo@gmail.com",rol=Roles.ADMINISTRADOR)

sesion = Sesion(id=usuario_prueba.id,rol=usuario_prueba.rol,usuario=usuario_prueba)

print(f'{len('073a90940a0046d88f42e6e0ee741231')=}')