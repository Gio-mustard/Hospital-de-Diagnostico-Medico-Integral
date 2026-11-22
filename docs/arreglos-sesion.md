# Arreglos al manejo de sesiones

Tres defectos que impedían que el inicio de sesión funcionara, corregidos sobre
el commit `wip(sesion)`. La suite queda en 622 pruebas, todas en verde.

## 1. Imports de `utils/auth.py`

Los imports de `sesion` y `sesion_repositorio` eran absolutos (`from
sesion_repositorio import ...`), así que el módulo no se podía importar:
`ModuleNotFoundError`. Eso tumbaba `tests/test_auth.py` y con él toda la suite.
Ahora son relativos, agrupados al final del bloque y sin el `SesionServicio`
duplicado que estaba importado dos veces.

De paso, `registrar` generaba el id con `str(uuid.uuid4())`, que mide 36
caracteres con guiones. `Usuario` exige exactamente 32 (`LONGITUD_UUID`) y el
DDL lo repite en `chk_usuario_id_uuid`, así que **ningún registro pasaba la
validación**. Vuelve a ser `uuid.uuid4().hex`.

## 2. `ingresar` devolvía una sesión distinta de la que guardaba

`SesionServicio.crear()` se llamaba dos veces: se persistía la primera sesión y
se retornaba una segunda, con otro id y otro token. Como la tabla guarda solo
el SHA-256 del token, el que recibía quien ingresaba no correspondía a ninguna
fila y `obtener_activa` le respondía `None` siempre. Ahora se crea una sola vez
y se devuelve esa misma.

El segundo problema era el orden. La comprobación de `usuario.activo` estaba
*después* de guardar, y `guardar` se confirma solo cuando no hay una
`transaccion()` abierta: al rechazar a un usuario dado de baja, su sesión ya
había quedado escrita, con su token vivo. La comprobación se movió antes de
abrir la sesión, conservando su posición después de verificar la contraseña y
su mensaje genérico, que es lo que evita enumerar los correos registrados.

Por último, el token ya llega al llavero del sistema:

```python
sesion = auth.ingresar(correo, contrasena, recordar=True)
```

`recordar` es explícito y por omisión `False`. Escribir en el llavero es un
efecto que sale de la base de datos y toca la máquina de quien usa el programa,
así que lo decide quien ingresa, no `Auth`. Además mantiene las pruebas fuera
del llavero real de quien las corre.

## 3. `guardar` resucitaba una sesión revocada

`revocar` no modifica la `Sesion` que recibe —es un dataclass congelado y la
verdad vive en la base—, así que el objeto en memoria conserva
`fecha_revocacion = None` para siempre. El `ON CONFLICT ... DO UPDATE` escribía
ese `None` de vuelta, de modo que cualquier `guardar` posterior reabría una
sesión cerrada y le devolvía el acceso a quien ya había salido:

```
revocar(s)   -> obtener_activa(s.token) == None   ✓
guardar(s)   -> obtener_activa(s.token) != None   ✗  la sesión volvió a vivir
```

`fecha_revocacion` salió del `DO UPDATE SET`, y el UPDATE lleva ahora un
`WHERE sesiones.fecha_revocacion IS NULL`, que también evita que se le corra el
vencimiento a una sesión ya cerrada. La única que escribe esa columna es
`revocar`. Una sesión viva se sigue pudiendo actualizar igual que antes.

## Servicio de sesión intercambiable

`SesionServicioArchivo` hereda de `SesionServicio` y reemplaza solo las tres
operaciones que tocan el almacenamiento: el token se guarda en
`sesion_prueba.txt` en lugar del llavero del sistema. `crear` se hereda tal
cual, para que el doble no pueda quedarse atrás si la entidad cambia.

Sirve para desarrollar: el llavero hay que estar autorizándolo, no deja ver qué
quedó guardado, y en una máquina sin escritorio (SSH, integración continua) no
hay backend y `keyring` revienta con `NoKeyringError`.

Al final de `utils/sesion.py` un interruptor decide cuál se exporta:

```python
USAR_SERVICIO_DE_PRUEBAS = True

if USAR_SERVICIO_DE_PRUEBAS:
    servicio_sesion: type[SesionServicio] = SesionServicioArchivo
else:
    servicio_sesion: type[SesionServicio] = SesionServicio
```

`utils/auth.py` importa `servicio_sesion` y no le consta cuál le tocó, así que
cambiar de almacenamiento es mover esa línea y nada más. **Hay que ponerlo en
`False` antes de entregar o de instalar la app en una máquina real.**

El archivo se crea con permisos `0600` y está en `.gitignore`, pero sigue
siendo una credencial viva en texto en claro: mientras no venza, quien lo lea
entra como quien lo generó.

## Cerrar sesión

`Auth.cerrar_sesion` cierra los dos lados de una sesión abierta:

```python
auth.cerrar_sesion()         # la sesión guardada en esta máquina
auth.cerrar_sesion(sesion)   # una en particular
```

- **En la base**, con `SesionRepositorio.revocar`, que ya existía y es la misma
  que corre contra la base en memoria de las pruebas y contra la real.
- **En la máquina**, con `servicio_sesion.limpiar()`, así que borra el token del
  llavero o del `.txt` según el interruptor, sin tener que saber cuál es.

Hay que cerrar los dos: borrar solo el token local deja la sesión viva hasta
que venza, y cualquiera que lo haya copiado sigue entrando.

Sin argumento restaura el token con `servicio_sesion.cargar()` y busca su
sesión, que es el caso de siempre —la app arrancó, restauró el token y quien la
usa aprieta salir sin tener a mano el objeto `Sesion`.

**El orden importa:** primero se revoca en la base y hasta después se borra el
token. Si se borrara antes y la escritura fallara, nos quedaríamos sin el único
dato que identifica esa sesión y seguiría abierta, sin forma de cerrarla hasta
vencer. Así un error se puede reintentar, y por eso un fallo al revocar sube tal
cual sin limpiar nada.

El token sí se borra aunque no haya sesión que revocar: ese es el caso de un
token vencido, ya revocado o de una base reinstalada, que no sirve para nada y
no tiene por qué seguir en el disco.

Devuelve `True` si había una sesión abierta que cerrar. Cerrar dos veces no es
un error: `revocar` no corre la hora del primer cierre, que es la que vale para
una auditoría. Para que eso fuera cierto también con el llavero real hubo que
hacer idempotente a `SesionServicio.limpiar`, que lanzaba
`PasswordDeleteError` cuando no había nada que borrar.

## Lo que falta
-> YA SE CORRIGIO
`tests/test_auth.py` se actualizó solo en lo indispensable: la firma nueva de
`Auth`, que ahora recibe el repositorio de sesiones. Siguen pendientes las
pruebas de regresión de estos defectos, `tests/test_sesion.py` completo,
restaurar la sesión al arrancar, revocar al cambiar la contraseña,
`revocar_todas` para cerrar de golpe las sesiones de un usuario, la degradación
cuando no hay backend de `keyring` y `keyring` en `requirements.txt`.
