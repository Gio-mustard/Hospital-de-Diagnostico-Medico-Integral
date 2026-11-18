# Ejemplo de 3 capas + coordinador en PySide6

App mínima (pacientes y médicos) que aplica el flujo que discutimos. Está en
una carpeta aparte a propósito: bórrala cuando acabes o úsala de molde.

## Correr

```bash
../env/bin/python main.py          # la app
../env/bin/python verificar_modelo.py   # la capa de modelo, sin abrir ventanas
```

## El mapa

```
main.py                  raíz de composición: decide QUÉ implementación se usa
app/
├── modelos/             Python puro, cero Qt
│   ├── entidades.py             dataclasses Paciente y Medico
│   ├── repositorios.py          las INTERFACES (ABC)
│   ├── repositorios_sqlite.py   implementación con SQL
│   ├── repositorios_memoria.py  implementación sin base de datos
│   └── conexion.py              conexión a SQLite
├── vistas/              solo interfaz: pinta y emite señales
│   ├── ventana_principal.py     emite pantalla_solicitada(str)
│   ├── ventana_pacientes.py     tabla + formulario
│   └── ventana_medicos.py       solo lista
└── controladores/
    ├── coordinador.py           crea controladores bajo demanda
    ├── controlador_pacientes.py
    └── controlador_medicos.py
```

## Las tres reglas, y dónde comprobarlas

**1. Las importaciones van en una sola dirección.** La vista nunca mira hacia
arriba; el modelo no conoce a nadie.

```bash
grep -rhE '^(from|import) ' app/vistas/*.py | grep -E 'modelos|controladores'
grep -rhE '^(from|import) ' app/modelos/*.py | grep -E 'vistas|PySide6'
```

Las dos búsquedas salen vacías. Esa es la prueba, no el dibujo.

**2. El modelo se usa sin abrir una ventana.** `verificar_modelo.py` ejercita
el CRUD completo y termina imprimiendo `Qt cargado: False` — ni se importó.

**3. La composición vive en un solo archivo.** En `main.py` están comentadas
las versiones de memoria. Descoméntalas, comenta las de SQLite, y la app corre
igual sin base de datos. Ese cambio de dos líneas es, exactamente, tu futura
migración a Supabase.

## El coordinador

En `coordinador.py`, `self.vivos` es un diccionario que hace dos trabajos:

- **caché**: si la clave no está, se construye el controlador; si está, se reusa.
  Nada se crea al arrancar (compruébalo: `vivos` está vacío hasta el primer clic).
- **referencia viva**: mientras la clave esté ahí, Python no recolecta el
  controlador, así que su ventana no se muere ni sus señales se desconectan.

La `VentanaPrincipal` solo emite `pantalla_solicitada("pacientes")`. No conoce
ningún controlador — ni sabe que existen.

## La decisión que dejé abierta

`ControladorPacientes.mostrar()` recarga la tabla en cada apertura. Es una de
las dos respuestas a la pregunta de la ventana cerrada y reabierta; la otra es
sacar el controlador de `vivos` al cerrarse. Las dos funcionan y tienen costos
distintos — ésa sigue siendo tu decisión.

## Lo que falta a propósito

Nada de Qt Designer (las ventanas están a mano para que se lean de corrido),
ningún `QAbstractTableModel` (la vista pinta un `QTableWidget`, que es más
simple), y ningún hilo. Los tres son el siguiente paso, no el primero.
