"""Permisos por rol: el decorador `autorizado`.

`AuthService` dice quién entró. Este módulo dice qué puede hacer cada quien.
Ingresar pasa una sola vez; el permiso se revisa en cada operación.

Cómo se usa
-----------

En el servicio, el permiso se escribe encima del método:

    from model.constants import Roles
    from utils.autorizacion import ServicioAutorizado, autorizado

    class ServicioEspecialidades(ServicioAutorizado):

        def __init__(self, auth: AuthService, repo: EspecialidadRepositorio):
            super().__init__(auth)            # el decorador busca este `auth`
            self.__repo = repo

        @autorizado(*Roles)                   # cualquiera que haya ingresado
        def consultar(self) -> tuple:
            return self.__repo.obtener_todos()

        @autorizado(Roles.ADMINISTRADOR)      # nada más el administrador
        def registrar(self, nombre: str) -> Especialidad:
            return self.__repo.registrar(Especialidad(nombre=nombre))

        @autorizado(Roles.ADMINISTRADOR, Roles.MEDICO)   # basta con uno
        def renombrar(self, especialidad: Especialidad, nombre: str) -> None:
            especialidad.nombre = nombre
            self.__repo.guardar(especialidad)
            print(f"lo cambió {self.sesion.usuario.correo}")

Adentro de un método decorado, `self.sesion` ya viene garantizada: si no
hubiera sesión, el decorador no habría dejado entrar.

En el controlador, que es el que le avisa al usuario. Son tres fallas
distintas y la ventana reacciona distinto a cada una:

    try:
        servicio.registrar(self.vista.campo_nombre.text())
    except SesionRequerida:                   # la sesión venció o se revocó
        self.volver_al_ingreso()
    except ErrorAutorizacion as error:        # ingresó, pero no le toca
        QMessageBox.warning(self.vista, "Sin permiso", str(error))
    except ValueError as error:               # el dato está mal
        QMessageBox.warning(self.vista, "Revisa los datos", str(error))

Mejor todavía es no ofrecer lo que no se puede. Cada método decorado lleva
colgada su lista de roles, así que la ventana puede preguntar antes de que el
usuario alcance a presionar:

    puede = sesion.usuario.rol in ServicioEspecialidades.registrar.roles_permitidos
    self.vista.boton_guardar.setEnabled(puede)

Reglas para no equivocarse
--------------------------

1.  El servicio hereda de `ServicioAutorizado` y le pasa el `auth` a
    `super().__init__`. Sin eso el decorador no encuentra la sesión, y lo
    dice con un TypeError en la primera llamada.

2.  Decora servicios, nunca repositorios. Un decorador solo cuida la puerta
    donde se le puso: si la ventana puede tomar el repositorio e ir directo a
    la tabla, el permiso se rodea sin esfuerzo. Por eso el repositorio se
    guarda privado y el único camino a la base es el servicio.

3.  No encadenes métodos decorados. Si uno decorado llama a otro, el de
    adentro vuelve a cobrar el permiso con su propia lista de roles y puede
    negar una operación que ya estaba permitida. Si dos operaciones comparten
    trabajo, sácalo a un método '_privado' SIN decorar y que las dos lo llamen.

4.  Los roles van como miembros del enum (`Roles.MEDICO`), no como texto. Un
    `@autorizado("Médico")` revienta al importar, a propósito: si se dejara
    pasar, la comparación nunca sería cierta y la operación le negaría a todo
    el mundo en silencio, que es mucho más difícil de notar.

5.  Ingresa con `recordar=True`. La sesión sale de `restaurar_sesion`, que lee
    el token guardado, y `ingresar` solo lo guarda cuando se le pide. Con
    `recordar=False` toda operación decorada queda fuera aunque el usuario
    acabe de entrar.

Por qué se le pregunta a la base cada vez
-----------------------------------------

El permiso no se revisa contra el objeto `Sesion` que devolvió `ingresar`,
sino contra la tabla, en cada llamada. `Sesion` es un dataclass congelado y
`revocar` no lo toca: una sesión ya cerrada sigue diciendo `activa == True` en
memoria para siempre. Preguntarle a ese objeto dejaría entrar a quien ya salió.

El que contesta es `AuthService.restaurar_sesion`, el único lugar del sistema
que decide si una sesión sirve: devuelve None si venció, si fue revocada o si
su usuario fue dado de baja. Así este módulo no repite nada de esa política;
nada más compara el rol.
"""

import functools
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar
from abc import ABC
from model.constants import Roles

from .autenticacion import AuthService
from .sesion import Sesion


class ErrorAutorizacion(Exception):
    """Raíz de los errores de permisos. Para atraparlos todos de un solo lado."""


class SesionRequerida(ErrorAutorizacion):
    """No hay sesión viva: hay que volver a ingresar.

    Separada de `PermisoDenegado` porque la vista reacciona distinto a cada
    una: esta manda a la pantalla de ingreso, la otra solo avisa que no se
    puede. Y ninguna de las dos es `ValueError`, que es lo que lanzan las
    validaciones de las entidades: un `except ValueError` puesto para mostrar
    "ese CURP no es válido" se tragaría un fallo de permisos sin decir nada.
    """

    def __init__(self, mensaje: str = "No hay una sesión activa. Vuelve a ingresar.") -> None:
        super().__init__(mensaje)


class PermisoDenegado(ErrorAutorizacion):
    """Hay sesión, pero el rol no alcanza para esta operación.

    Guarda el rol que se tenía y los que se pedían, por si la vista quiere
    decir qué hacía falta. El mensaje no menciona datos del usuario.
    """

    def __init__(self, rol: Roles, permitidos: tuple[Roles, ...]) -> None:
        self.rol = rol
        self.permitidos = permitidos
        nombres = ", ".join(miembro.value for miembro in permitidos)
        super().__init__(
            f"Un {rol.value} no puede realizar esta acción; es para: {nombres}."
        )


P = ParamSpec("P")
R = TypeVar("R")

def autorizado(
    *roles: Roles,
) -> Callable[[Callable[Concatenate[Any, P], R]], Callable[Concatenate[Any, P], R]]:
    """Deja pasar la llamada solo si el rol de la sesión viva es uno de `roles`.

    Basta con cumplir UNO de los roles recibidos. Varios roles y no uno porque
    apilar dos decoradores no sirve para eso: `@autorizado(A)` sobre
    `@autorizado(B)` exige los dos a la vez, que es imposible, y la operación
    quedaría muerta sin que nadie lo notara.

    Son tres niveles y no dos, que es el error más fácil de cometer aquí:

        autorizado(Roles.MEDICO)      <- la fábrica: recibe los roles
          decorador(funcion)          <- recibe la función, una sola vez, al
                                         definirse la clase
            envoltura(objeto, *args)  <- recibe la llamada, cada vez

    Si los roles se pidieran en la envoltura serían un argumento que el que
    llama tendría que pasar, y en un método se comerían el `self`. Van en la
    fábrica: ahí se leen una vez al importar y quedan fijos en la clausura.

    El método decorado tiene que ser de un objeto con un `auth`, normalmente
    heredando de `ServicioAutorizado`.

    Lanza `SesionRequerida` si no hay sesión viva y `PermisoDenegado` si la hay
    pero el rol no alcanza. Las dos antes de que el cuerpo del método corra:
    una operación negada no deja nada a medias.

    El `self` va tipado como `Any` porque amarrarlo a un tipo hace que el
    verificador se queje en cada servicio que además herede de otra cosa. El
    resto de la firma sí se conserva (`ParamSpec` + `functools.wraps`), que es
    lo que hace que el editor siga autocompletando los argumentos del método
    decorado.
    """
    
    if not roles or not all(isinstance(rol, Roles) for rol in roles):
        raise TypeError(
            "@autorizado necesita al menos un rol del enum Roles: "
            "@autorizado(Roles.MEDICO)."
        )

    def decorador(funcion: Callable[Concatenate[Any, P], R]) -> Callable[Concatenate[Any, P], R]:
        @functools.wraps(funcion)
        def envoltura(objeto: Any, *args: P.args, **kwargs: P.kwargs) -> R:
            sesion = _sesion_del_objeto(objeto, funcion)
            if sesion is None:
                raise SesionRequerida()

            if sesion.usuario.rol not in roles:
                raise PermisoDenegado(sesion.usuario.rol, roles)

            return funcion(objeto, *args, **kwargs)

        envoltura.roles_permitidos = roles  # type: ignore[attr-defined]
        return envoltura

    return decorador


def _sesion_del_objeto(objeto: Any, funcion: Callable) -> Sesion | None:
    """Pide la sesión viva al `auth` del objeto que recibió la llamada.

    El decorador no puede comprobar al decorar que la clase traiga un `auth`,
    porque cuando corre todavía no existe la clase: solo hay una función. Así
    que el aviso llega en la primera llamada, pero dice exactamente qué falta.
    """
    auth = getattr(objeto, "auth", None)
    if not isinstance(auth, AuthService):
        raise TypeError(
            f"@autorizado decora métodos de un objeto con un AuthService en "
            f"`auth`, y {type(objeto).__name__}.{funcion.__name__} no lo "
            f"tiene. Hereda de ServicioAutorizado."
        )
    return auth.restaurar_sesion()


class ServicioAutorizado(ABC):
    """Base de los servicios cuyas operaciones dependen de quién las pide.

    Aporta el `auth` que `autorizado` busca y un `sesion` ya garantizado para
    usarse dentro de un método decorado.

    `auth` es público porque el decorador lo lee desde fuera de la clase: con
    dos guiones bajos, el *name mangling* lo dejaría como `_Servicio__auth` y
    la envoltura no lo encontraría.
    """

    def __init__(self, auth: AuthService) -> None:
        self.auth = auth

    @property
    def sesion(self) -> Sesion:
        """La sesión viva, o `SesionRequerida`.

        Para usarse dentro de un método decorado, donde el decorador ya
        comprobó que hay sesión: ahí `self.sesion.usuario` no puede ser None y
        no hay que escribir el `if` cada vez.
        """
        sesion = self.auth.restaurar_sesion()
        if sesion is None:
            raise SesionRequerida()
        return sesion
