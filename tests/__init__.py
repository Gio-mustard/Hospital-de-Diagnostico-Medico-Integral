"""Pruebas del proyecto.

Se construyen sobre `unittest`, de la libreria estandar, por la misma razon por
la que la base de datos es sqlite3: no agrega ninguna dependencia nueva al
`requirements.txt` y corre con el interprete del entorno tal como esta.

COMO CORRERLAS

    ./env/bin/python -m tests              # todas, con resumen legible
    ./env/bin/python -m tests cita         # solo las que mencionen "cita"
    ./env/bin/python -m tests -q           # solo el resumen final

Tambien funciona unittest directo. El `-t .` es necesario porque los modulos
de prueba se importan entre si con imports relativos (`from .base import ...`),
asi que la raiz del proyecto tiene que ser el paquete de nivel superior:

    ./env/bin/python -m unittest discover -s tests -t . -v
    ./env/bin/python -m unittest tests.test_cita -v
    ./env/bin/python -m unittest tests.test_cita.DarBajaCita -v

COMO ESTAN ARMADAS

`base.py` tiene `RepositorioTestCase`: levanta una base de datos SQLite en
memoria, le aplica `ddl.sql` completo (el mismo archivo que usa la app, no una
copia recortada) y ofrece fabricas para los datos de prueba. Cada prueba recibe
una base recien creada, asi que no hay orden ni estado compartido entre ellas.
"""
