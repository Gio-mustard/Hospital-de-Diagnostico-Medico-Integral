
from dataclasses import dataclass
from model.trabajador import Trabajador
from model.medico import Medico


@dataclass(frozen=True)
class Sesion():
    usuario:Trabajador
    token

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
)

sesion = Sesion(medico_prueba)

print(f'{sesion=}')