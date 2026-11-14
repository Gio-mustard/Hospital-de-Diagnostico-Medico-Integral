# SQLite en Python con `sqlite3`

`sqlite3` es el módulo de la **librería estándar** de Python: no se instala con
pip, ya viene incluido con Python. Toda la base de datos vive en un solo
archivo, lo cual es ideal para una aplicación de escritorio.

```python
import sqlite3
print(sqlite3.sqlite_version)   # versión del motor SQLite
```

---

## 1. Conectarse

```python
import sqlite3

cx = sqlite3.connect("hospital.db")   # crea el archivo si no existe
...
cx.commit()                           # guarda los cambios
cx.close()
```

- `connect(":memory:")` crea una base de datos en RAM: perfecta para pruebas.
- La conexión **no** guarda nada hasta que haces `commit()`.
- `connect()` acepta también un objeto `Path` de `pathlib`.

### Cursor o atajo

Se puede trabajar con un cursor explícito o directo sobre la conexión (que
crea el cursor por dentro y lo devuelve):

```python
cur = cx.cursor()
cur.execute("SELECT 1")

cur = cx.execute("SELECT 1")     # equivalente y más corto
```

### Filas accesibles por nombre de columna

Por defecto cada fila es una tupla (`fila[0]`, `fila[1]`…). Con
`row_factory = sqlite3.Row` puedes usar el nombre de la columna:

```python
cx.row_factory = sqlite3.Row

fila = cx.execute("SELECT id, nombre FROM paciente WHERE id = 1").fetchone()
print(fila["nombre"])       # por nombre
print(fila[1])              # sigue funcionando por posición
print(dict(fila))           # {'id': 1, 'nombre': 'Ana'}
```

### Activar las llaves foráneas (importante)

SQLite ignora las `FOREIGN KEY` si no las activas **en cada conexión**:

```python
cx.execute("PRAGMA foreign_keys = ON")
```

Sin esto, puedes borrar un paciente y dejar sus citas apuntando a un id que ya
no existe.

### Un patrón cómodo para abrir la conexión

```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def conectar(ruta="hospital.db"):
    """Abre la conexión, hace COMMIT al salir, ROLLBACK si truena, y cierra."""
    cx = sqlite3.connect(ruta)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys = ON")
    try:
        yield cx
        cx.commit()
    except Exception:
        cx.rollback()
        raise
    finally:
        cx.close()


with conectar() as cx:
    for fila in cx.execute("SELECT nombre FROM paciente"):
        print(fila["nombre"])
```

---

## 2. Crear las tablas

`executescript()` ejecuta varias sentencias separadas por `;`:

```python
cx.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS paciente (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre            TEXT    NOT NULL,
        apellido_paterno  TEXT    NOT NULL,
        curp              TEXT    UNIQUE,
        fecha_nacimiento  TEXT,                 -- ISO: AAAA-MM-DD
        sexo              TEXT    CHECK (sexo IN ('M', 'F', 'O')),
        creado_en         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS cita (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL REFERENCES paciente(id) ON DELETE CASCADE,
        fecha_hora  TEXT    NOT NULL,           -- 'AAAA-MM-DD HH:MM'
        estado      TEXT    NOT NULL DEFAULT 'programada'
                            CHECK (estado IN ('programada', 'atendida', 'cancelada'))
    );

    CREATE INDEX IF NOT EXISTS idx_cita_fecha ON cita(fecha_hora);
""")
```

Con `IF NOT EXISTS` el script se puede correr cada vez que arranca el programa
sin romper nada.

Si prefieres tener el DDL en un archivo `.sql` aparte:

```python
from pathlib import Path

cx.executescript(Path("esquema.sql").read_text(encoding="utf-8"))
```

---

## 3. Insertar (INSERT)

**Nunca** metas los valores con f-strings: usa parámetros. Así evitas la
inyección de SQL y los problemas con comillas y acentos.

```python
# MAL  ❌  (inyección de SQL)
cx.execute(f"INSERT INTO paciente (nombre) VALUES ('{nombre}')")

# BIEN ✅  parámetros posicionales
cx.execute("INSERT INTO paciente (nombre, apellido_paterno) VALUES (?, ?)",
           ("Ana", "López"))

# BIEN ✅  parámetros con nombre
cx.execute("INSERT INTO paciente (nombre, apellido_paterno) VALUES (:nombre, :apellido)",
           {"nombre": "Ana", "apellido": "López"})
```

### Obtener el id recién insertado

```python
cur = cx.execute("INSERT INTO paciente (nombre, apellido_paterno) VALUES (?, ?)",
                 ("Ana", "López"))
print(cur.lastrowid)        # -> 1
```

### Insertar muchos registros de una vez

```python
estudios = [
    ("BH",       "Biometría hemática",  "Laboratorio",  350.0),
    ("QS6",      "Química sanguínea 6", "Laboratorio",  480.0),
    ("RX-TORAX", "Rayos X de tórax",    "Imagenología", 700.0),
]
cx.executemany(
    "INSERT INTO estudio (clave, nombre, area, precio) VALUES (?, ?, ?, ?)",
    estudios,
)
```

### Insertar o ignorar / actualizar si ya existe

```python
# No truena si la CURP ya está registrada
cx.execute("INSERT OR IGNORE INTO paciente (nombre, curp) VALUES (?, ?)", datos)

# UPSERT: si la CURP existe, actualiza el teléfono
cx.execute("""
    INSERT INTO paciente (nombre, curp, telefono) VALUES (?, ?, ?)
    ON CONFLICT(curp) DO UPDATE SET telefono = excluded.telefono
""", ("Ana", "LOPA900101MDFNNA01", "3311111111"))
```

---

## 4. Consultar (SELECT)

```python
cur = cx.execute("SELECT * FROM paciente WHERE apellido_paterno = ?", ("López",))

cur.fetchone()      # una fila (o None si no hay)
cur.fetchall()      # lista con todas las filas
cur.fetchmany(10)   # las siguientes 10 filas
```

Ojo con el detalle clásico: para un solo parámetro la tupla necesita la coma,
`("López",)`. Sin ella no es una tupla y Python marca error.

También puedes iterar el cursor directamente, que gasta menos memoria:

```python
for fila in cx.execute("SELECT nombre FROM paciente ORDER BY nombre"):
    print(fila["nombre"])
```

### Un solo valor (COUNT, SUM…)

```python
total = cx.execute("SELECT COUNT(*) FROM paciente").fetchone()[0]
```

### Búsquedas parciales con LIKE

```python
texto = "lóp"
cx.execute(
    "SELECT * FROM paciente WHERE apellido_paterno LIKE '%' || ? || '%'",
    (texto,),
)
```

El `||` concatena en SQL. Fíjate que los `%` van **fuera** del parámetro.

### Filtro opcional (buscador vacío = todos)

Muy útil para una caja de búsqueda en la interfaz:

```python
sql = """
    SELECT * FROM paciente
    WHERE (:q = '' OR nombre LIKE '%' || :q || '%'
                   OR curp   LIKE '%' || :q || '%')
    ORDER BY apellido_paterno, nombre
"""
cx.execute(sql, {"q": texto_del_cuadro_de_busqueda})
```

### Listas en un `IN (...)`

No puedes pasar una lista a un solo `?`; hay que generar los marcadores:

```python
ids = [1, 2, 5]
marcadores = ", ".join("?" * len(ids))          # "?, ?, ?"
cx.execute(f"SELECT * FROM paciente WHERE id IN ({marcadores})", ids)
```

Aquí el f-string es seguro porque sólo arma signos de interrogación: los
valores siguen yendo parametrizados.

### Un JOIN

```python
sql = """
    SELECT  c.fecha_hora,
            p.nombre || ' ' || p.apellido_paterno AS paciente,
            e.nombre AS estudio,
            e.precio
    FROM        cita         AS c
    JOIN        paciente     AS p  ON p.id = c.paciente_id
    JOIN        cita_estudio AS ce ON ce.cita_id = c.id
    JOIN        estudio      AS e  ON e.id = ce.estudio_id
    WHERE   date(c.fecha_hora) = date('now', 'localtime')
    ORDER BY c.fecha_hora
"""
for fila in cx.execute(sql):
    print(fila["fecha_hora"], fila["paciente"], fila["estudio"])
```

---

## 5. Actualizar y borrar

`rowcount` dice cuántas filas se vieron afectadas:

```python
cur = cx.execute("UPDATE paciente SET telefono = ? WHERE id = ?",
                 ("3311111111", 1))
print(cur.rowcount)        # 1 si existía ese paciente, 0 si no

cur = cx.execute("DELETE FROM paciente WHERE id = ?", (1,))
print(cur.rowcount)
```

### Actualizar sólo los campos que llegaron

Cuando un formulario manda unos cuantos campos, se arma el `SET` sobre una
lista blanca de columnas (los **nombres** de columna no pueden ir como
parámetro; los **valores** sí):

```python
def actualizar_paciente(cx, paciente_id, **campos):
    permitidos = {"nombre", "apellido_paterno", "curp", "telefono", "email"}
    campos = {k: v for k, v in campos.items() if k in permitidos}
    if not campos:
        return 0
    asignaciones = ", ".join(f"{col} = :{col}" for col in campos)
    sql = f"UPDATE paciente SET {asignaciones} WHERE id = :id"
    return cx.execute(sql, {**campos, "id": paciente_id}).rowcount
```

---

## 6. Transacciones

Varias operaciones que deben pasar **todas o ninguna** (por ejemplo, crear una
cita y sus estudios):

```python
try:
    cita_id = cx.execute(
        "INSERT INTO cita (paciente_id, fecha_hora) VALUES (?, ?)",
        (1, "2026-11-20 09:30"),
    ).lastrowid

    cx.executemany(
        "INSERT INTO cita_estudio (cita_id, estudio_id) VALUES (?, ?)",
        [(cita_id, 1), (cita_id, 3)],
    )
    cx.commit()            # ambas cosas quedan guardadas
except sqlite3.Error:
    cx.rollback()          # no queda nada a medias
    raise
```

La conexión también sirve como context manager: hace `commit` al salir bien y
`rollback` si hay una excepción (pero **no** cierra la conexión):

```python
with sqlite3.connect("hospital.db") as cx:
    cx.execute("INSERT INTO paciente (nombre, apellido_paterno) VALUES (?, ?)",
               ("Ana", "López"))
# aquí ya se hizo commit
```

---

## 7. Errores comunes

```python
import sqlite3

try:
    cx.execute("INSERT INTO paciente (nombre, apellido_paterno, curp) VALUES (?, ?, ?)",
               ("Ana", "López", "LOPA900101MDFNNA01"))
except sqlite3.IntegrityError as error:
    # UNIQUE, NOT NULL, CHECK o FOREIGN KEY no se cumplieron
    print("Dato inválido o repetido:", error)
except sqlite3.OperationalError as error:
    # tabla o columna que no existe, SQL mal escrito, archivo bloqueado
    print("Error de SQL:", error)
```

`sqlite3.Error` es el padre de todas; `IntegrityError` y `OperationalError`
son las que verás casi siempre. En la interfaz conviene atraparlas y mostrar
el mensaje en un `QMessageBox` en lugar de dejar que truene el programa.

---

## 8. Tipos de datos y fechas

SQLite guarda `NULL`, `INTEGER`, `REAL`, `TEXT` y `BLOB`. La conversión con
Python es directa:

| Python           | SQLite    |
|------------------|-----------|
| `None`           | `NULL`    |
| `int`            | `INTEGER` |
| `float`          | `REAL`    |
| `str`            | `TEXT`    |
| `bytes`          | `BLOB`    |
| `True` / `False` | `1` / `0` |

**No hay tipo fecha.** Se guardan como texto ISO (`'2026-11-20 09:30'`), que
ordena y compara correctamente:

```python
from datetime import date, datetime

cx.execute("INSERT INTO cita (paciente_id, fecha_hora) VALUES (?, ?)",
           (1, datetime(2026, 11, 20, 9, 30).strftime("%Y-%m-%d %H:%M")))

# De vuelta a objeto de Python
fila = cx.execute("SELECT fecha_nacimiento FROM paciente WHERE id = 1").fetchone()
nacimiento = date.fromisoformat(fila["fecha_nacimiento"])
```

Funciones de fecha de SQLite que te van a servir:

```sql
SELECT date('now', 'localtime');                   -- hoy
SELECT datetime('now', '+1 day');                  -- mañana
SELECT strftime('%Y-%m-%d', fecha_hora) AS dia FROM cita;
SELECT (strftime('%Y', 'now') - strftime('%Y', fecha_nacimiento)) AS edad
FROM   paciente;
```

---

## 9. Junto con una interfaz de PySide6

### Separa el SQL de la ventana

Conviene que la ventana no escriba SQL: que llame a funciones (un
"repositorio") que reciben y devuelven datos. Así el SQL se prueba sin abrir
ninguna ventana y no se repite en cada pantalla.

```python
# datos.py
def listar_pacientes(busqueda=""):
    with conectar() as cx:
        return cx.execute(
            "SELECT * FROM paciente WHERE nombre LIKE '%' || ? || '%'",
            (busqueda,),
        ).fetchall()

# ventana.py
filas = listar_pacientes(self.caja_busqueda.text())
```

### Consultas lentas: no congeles la ventana

Una consulta larga en el hilo de la interfaz deja la ventana congelada. Para
esos casos usa `QThreadPool` con un `QRunnable`:

```python
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

class Señales(QObject):
    listo = Signal(list)

class TareaConsulta(QRunnable):
    def __init__(self):
        super().__init__()
        self.señales = Señales()

    def run(self):
        self.señales.listo.emit(listar_pacientes())   # conexión propia del hilo

tarea = TareaConsulta()
tarea.señales.listo.connect(self.pintar_tabla)        # se ejecuta en la interfaz
QThreadPool.globalInstance().start(tarea)
```

> Importante: un objeto `sqlite3.Connection` no debe compartirse entre hilos.
> Abre una conexión nueva dentro del hilo.

### Alternativa: QtSql (driver `QSQLITE`)

PySide6 trae su propio módulo de bases de datos. Sirve para conectar una tabla
directo a un `QTableView` sin escribir el pintado a mano:

```python
from PySide6.QtSql import QSqlDatabase, QSqlTableModel
from PySide6.QtWidgets import QTableView

bd = QSqlDatabase.addDatabase("QSQLITE")
bd.setDatabaseName("hospital.db")
bd.open()

modelo = QSqlTableModel()
modelo.setTable("paciente")
modelo.select()

vista = QTableView()
vista.setModel(modelo)      # edición de la tabla casi gratis
```

Son dos caminos distintos para la misma base de datos: `sqlite3` te deja
escribir el SQL del taller, `QtSql` te ahorra código en la interfaz. Se puede
usar uno, el otro, o los dos.

---

## 10. Utilidades

```python
# ¿Qué tablas hay?
cx.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()

# ¿Cómo está formada una tabla?
cx.execute("PRAGMA table_info(paciente)").fetchall()

# Ver el plan de ejecución (para saber si usa un índice)
cx.execute("EXPLAIN QUERY PLAN SELECT * FROM paciente WHERE curp = ?", ("X",)).fetchall()

# Respaldo en caliente a otro archivo
with sqlite3.connect("respaldo.db") as destino:
    cx.backup(destino)
```

Desde la terminal:

```bash
sqlite3 hospital.db ".tables"
sqlite3 hospital.db ".schema paciente"
sqlite3 hospital.db "SELECT * FROM paciente;"
```

---

## Referencias

- Módulo `sqlite3`: https://docs.python.org/es/3/library/sqlite3.html
- SQL que entiende SQLite: https://www.sqlite.org/lang.html
- Funciones de fecha y hora: https://www.sqlite.org/lang_datefunc.html
- `QtSql` en PySide6: https://doc.qt.io/qtforpython-6/PySide6/QtSql/index.html
