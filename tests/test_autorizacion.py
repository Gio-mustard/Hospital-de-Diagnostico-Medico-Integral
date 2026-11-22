"""Pruebas del decorador `autorizado`.

Lo que importa aqui es que el permiso no se pueda rodear, y en particular que
no se decida con el objeto `Sesion` que devolvio `ingresar`: ese es un
dataclass congelado y sigue diciendo que esta activa aunque la hayan revocado.
Por eso las pruebas usan el `AuthService` real contra la base en memoria, y
revocan o caducan escribiendo en la tabla, como pasaria de verdad.

El doble del servicio de sesion se toma prestado de `test_auth`, que ya lo
tiene explicado, para no tener dos copias que se separen. Si algun dia lo
necesita un tercer modulo, su lugar es `tests/base.py`.
"""

import inspect
import unittest

import utils.autenticacion as modulo_autenticacion
from model.constants import Roles
from model.repositories import UsuarioSQLRepository
from utils.autenticacion import AuthService
from utils.autorizacion import (
    ErrorAutorizacion,
    PermisoDenegado,
    ServicioAutorizado,
    SesionRequerida,
    autorizado,
)
from utils.sesion import Sesion
from utils.sesion_repositorio import SesionSQLRepositorio

from .base import RepositorioTestCase
from .test_auth import ServicioSesionMemoria

CONTRASENA = "contrasena-valida-123"

_costo_real = None


def setUpModule():
    """Baja el costo de bcrypt mientras corren estas pruebas.

    Cada prueba registra un usuario y entra con el, o sea dos hasheos, y a
    2^12 rondas eso serian ~0.7 s por prueba. Lo que se ejercita aqui son los
    permisos, no la dureza del hash. Mismo trato que en `test_auth`.
    """
    global _costo_real
    _costo_real = modulo_autenticacion.COSTO_BCRYPT
    modulo_autenticacion.COSTO_BCRYPT = 4


def tearDownModule():
    modulo_autenticacion.COSTO_BCRYPT = _costo_real


class ServicioDePrueba(ServicioAutorizado):
    """Un servicio de mentiras con una operacion por caso que se prueba.

    `llamadas` cuenta los cuerpos que de verdad corrieron: es la forma de
    comprobar que una operacion negada no alcanza a tocar nada.
    """

    def __init__(self, auth: AuthService) -> None:
        super().__init__(auth)
        self.llamadas: list[str] = []

    @autorizado(Roles.MEDICO)
    def solo_medico(self) -> str:
        self.llamadas.append("solo_medico")
        return "receta"

    @autorizado(Roles.MEDICO, Roles.ADMINISTRADOR)
    def medico_o_admin(self) -> str:
        self.llamadas.append("medico_o_admin")
        return "historial"

    @autorizado(Roles.ADMINISTRADOR)
    def solo_admin(self) -> str:
        self.llamadas.append("solo_admin")
        return "usuarios"

    @autorizado(*Roles)
    def cualquiera_que_ingreso(self) -> str:
        self.llamadas.append("cualquiera_que_ingreso")
        return "catalogo"

    @autorizado(Roles.MEDICO)
    def con_argumentos(self, uno: int, dos: int = 0, *, tres: int = 0) -> int:
        """Suma, para ver que los argumentos pasan tal cual."""
        self.llamadas.append("con_argumentos")
        return uno + dos + tres

    @autorizado(Roles.MEDICO)
    def quien_soy(self) -> str:
        """Usa `self.sesion` desde dentro, que es su unico uso legitimo."""
        return self.sesion.usuario.correo

    @autorizado(Roles.MEDICO)
    def compuesta(self) -> str:
        """Operacion decorada que llama a otra del mismo rol."""
        self.llamadas.append("compuesta")
        return self.solo_medico()

    @autorizado(Roles.MEDICO)
    def llama_a_la_de_admin(self) -> str:
        """Un medico entra aqui, pero no deberia poder seguir hacia adentro."""
        self.llamadas.append("llama_a_la_de_admin")
        return self.solo_admin()


class SinAuth:
    """Un objeto que no trae `auth`, para ver que se avisa y como."""

    @autorizado(Roles.MEDICO)
    def operacion(self) -> None: ...


class ConUnAuthFalso:
    """Un objeto con un `auth` que no es un AuthService."""

    def __init__(self) -> None:
        self.auth = "no soy un AuthService"

    @autorizado(Roles.MEDICO)
    def operacion(self) -> None: ...


class SesionesQueCuentan(SesionSQLRepositorio):
    """El repositorio de sesiones, contando cuantas veces se revalida."""

    def __init__(self, db, usuario_repo) -> None:
        super().__init__(db, usuario_repo)
        self.consultas = 0

    def obtener_activa(self, token: str) -> Sesion | None:
        self.consultas += 1
        return super().obtener_activa(token)


class AutorizacionTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.usuarios = UsuarioSQLRepository(self.db)
        self.sesiones = SesionesQueCuentan(self.db, self.usuarios)
        self.servicio_sesion = ServicioSesionMemoria()
        self.auth = AuthService(self.usuarios, self.sesiones, self.servicio_sesion)
        self.servicio = ServicioDePrueba(self.auth)

    def ingresar(self, rol: Roles = Roles.MEDICO, *, recordar: bool = True) -> Sesion:
        """Da de alta un usuario de ese rol y entra con el.

        `recordar=True` por omision porque el decorador saca la sesion de
        `restaurar_sesion`, que lee el token guardado: sin recordar no habria
        nada que restaurar. Esa consecuencia tiene su propia prueba.
        """
        correo = f"usuario{self._siguiente()}@hospital.com"
        self.auth.registrar(correo, CONTRASENA, rol)
        return self.auth.ingresar(correo, CONTRASENA, recordar=recordar)

    def caducar(self, sesion: Sesion) -> None:
        """Vence la sesion en la tabla, sin esperar las 8 horas.

        Se escribe el texto directo en la columna porque es el formato con el
        que `obtener_activa` compara (`fecha_expiracion > ?`, texto ISO UTC), y
        porque `Sesion` es un dataclass congelado: la fecha del objeto no se
        puede correr.
        """
        self.db.execute(
            "UPDATE sesiones SET fecha_expiracion = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", sesion.id),
        )


class RolQueDejaPasar(AutorizacionTestCase):
    def test_el_rol_exacto_pasa(self):
        self.ingresar(Roles.MEDICO)

        self.assertEqual(self.servicio.solo_medico(), "receta")
        self.assertEqual(self.servicio.llamadas, ["solo_medico"])

    def test_cualquiera_de_los_roles_listados_pasa(self):
        for rol in (Roles.MEDICO, Roles.ADMINISTRADOR):
            with self.subTest(rol=rol):
                self.setUp()
                self.ingresar(rol)
                self.assertEqual(self.servicio.medico_o_admin(), "historial")

    def test_con_todos_los_roles_pasa_cualquiera_que_haya_ingresado(self):
        """`@autorizado(*Roles)`, que es el idioma para 'cualquier sesion'."""
        for rol in Roles:
            with self.subTest(rol=rol):
                self.setUp()
                self.ingresar(rol)
                self.assertEqual(self.servicio.cualquiera_que_ingreso(), "catalogo")

    def test_los_argumentos_llegan_sin_tocarse(self):
        self.ingresar(Roles.MEDICO)

        self.assertEqual(self.servicio.con_argumentos(1, 2, tres=3), 6)
        self.assertEqual(self.servicio.con_argumentos(1), 1)

    def test_adentro_la_sesion_esta_garantizada(self):
        sesion = self.ingresar(Roles.MEDICO)

        self.assertEqual(self.servicio.quien_soy(), sesion.usuario.correo)

    def test_una_operacion_llama_a_otra_del_mismo_rol(self):
        self.ingresar(Roles.MEDICO)

        self.assertEqual(self.servicio.compuesta(), "receta")
        self.assertEqual(self.servicio.llamadas, ["compuesta", "solo_medico"])


class RolQueNoAlcanza(AutorizacionTestCase):
    def test_otro_rol_recibe_permiso_denegado(self):
        self.ingresar(Roles.ENFERMERO)

        with self.assertRaises(PermisoDenegado):
            self.servicio.solo_medico()

    def test_la_operacion_negada_no_corre_su_cuerpo(self):
        self.ingresar(Roles.ENFERMERO)

        with self.assertRaises(PermisoDenegado):
            self.servicio.solo_medico()

        self.assertEqual(self.servicio.llamadas, [])

    def test_ningun_rol_de_fuera_de_la_lista_pasa(self):
        for rol in (Roles.ENFERMERO, Roles.RECEPCIONISTA):
            with self.subTest(rol=rol):
                self.setUp()
                self.ingresar(rol)
                with self.assertRaises(PermisoDenegado):
                    self.servicio.medico_o_admin()

    def test_el_error_dice_que_rol_habia_y_cuales_hacian_falta(self):
        self.ingresar(Roles.ENFERMERO)

        with self.assertRaises(PermisoDenegado) as capturado:
            self.servicio.medico_o_admin()

        self.assertIs(capturado.exception.rol, Roles.ENFERMERO)
        self.assertEqual(
            capturado.exception.permitidos, (Roles.MEDICO, Roles.ADMINISTRADOR)
        )

    def test_el_mensaje_no_filtra_datos_del_usuario(self):
        sesion = self.ingresar(Roles.ENFERMERO)

        with self.assertRaises(PermisoDenegado) as capturado:
            self.servicio.solo_medico()

        mensaje = str(capturado.exception)
        self.assertNotIn(sesion.usuario.correo, mensaje)
        self.assertNotIn(sesion.usuario.id, mensaje)
        self.assertNotIn(sesion.token, mensaje)

    def test_el_permiso_se_vuelve_a_cobrar_hacia_adentro(self):
        """Entrar a la externa no autoriza lo que esa externa llame despues.

        Es la razon de la regla de no encadenar metodos decorados: aqui el
        medico tenia permiso de la operacion que pidio, y aun asi se queda a
        medias porque la de adentro es de administrador.
        """
        self.ingresar(Roles.MEDICO)

        with self.assertRaises(PermisoDenegado):
            self.servicio.llama_a_la_de_admin()

        self.assertEqual(self.servicio.llamadas, ["llama_a_la_de_admin"])


class SinSesionViva(AutorizacionTestCase):
    def test_sin_haber_ingresado_no_se_puede_nada(self):
        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_una_sesion_revocada_no_sirve_aunque_el_objeto_diga_que_vive(self):
        sesion = self.ingresar(Roles.MEDICO)
        self.sesiones.revocar(sesion)

        # El objeto congelado sigue convencido de que esta activa: es
        # exactamente el engano del que tiene que protegernos el decorador.
        self.assertTrue(sesion.activa)

        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_una_sesion_caducada_no_sirve(self):
        sesion = self.ingresar(Roles.MEDICO)
        self.caducar(sesion)

        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_un_usuario_dado_de_baja_no_sirve(self):
        sesion = self.ingresar(Roles.MEDICO)
        self.usuarios.darbaja(sesion.usuario)

        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_cerrar_sesion_deja_fuera(self):
        self.ingresar(Roles.MEDICO)
        self.auth.cerrar_sesion()

        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_sin_recordar_queda_fuera_aunque_acabe_de_entrar(self):
        """Documenta la consecuencia de que la sesion salga de `auth`.

        `ingresar(recordar=False)` no guarda el token, y `restaurar_sesion` lo
        lee de ahi: el decorador no tiene como encontrar la sesion. La sesion
        SI existe y esta viva en la tabla, lo que falta es el token guardado.
        Si algun dia `ingresar` guarda el token siempre, esta prueba es la que
        tiene que cambiar.
        """
        sesion = self.ingresar(Roles.MEDICO, recordar=False)

        self.assertIsNotNone(self.sesiones.obtener_activa(sesion.token))
        self.assertIsNone(self.servicio_sesion.cargar())
        with self.assertRaises(SesionRequerida):
            self.servicio.solo_medico()

    def test_las_dos_fallas_se_atrapan_juntas(self):
        """Un `except ErrorAutorizacion` en la vista cubre los dos casos."""
        with self.assertRaises(ErrorAutorizacion):
            self.servicio.solo_medico()

        self.ingresar(Roles.ENFERMERO)
        with self.assertRaises(ErrorAutorizacion):
            self.servicio.solo_medico()

    def test_el_error_de_permisos_no_es_un_error_de_validacion(self):
        """Nunca ValueError: lo lanzan las entidades y se confundirian.

        El controlador atrapa las tres por separado, y si una heredara de la
        otra el orden de los `except` decidiria el dialogo que ve el usuario.
        """
        self.assertFalse(issubclass(ErrorAutorizacion, ValueError))
        self.assertFalse(issubclass(ValueError, ErrorAutorizacion))


class BaseDeLosServicios(AutorizacionTestCase):
    """Lo que aporta `ServicioAutorizado`."""

    def test_el_auth_inyectado_es_el_que_se_usa(self):
        self.assertIs(self.servicio.auth, self.auth)

    def test_la_sesion_se_puede_pedir_sin_decorador(self):
        sesion = self.ingresar(Roles.MEDICO)

        self.assertEqual(self.servicio.sesion.usuario.correo, sesion.usuario.correo)

    def test_pedir_la_sesion_sin_haber_ingresado_revienta(self):
        with self.assertRaises(SesionRequerida):
            self.servicio.sesion

    def test_cada_llamada_decorada_revalida_contra_la_base(self):
        """El precio de no cachear la sesion: una consulta por nivel.

        `compuesta` llama a `solo_medico`, y son dos consultas porque cada
        decorador vuelve a preguntar si la sesion sigue viva. Es a cambio de
        que una sesion revocada no alcance a colarse ni a media operacion.
        """
        self.ingresar(Roles.MEDICO)
        self.sesiones.consultas = 0

        self.servicio.compuesta()

        self.assertEqual(self.sesiones.consultas, 2)


class FormaDelDecorador(unittest.TestCase):
    """No toca la base: solo como queda la funcion decorada."""

    def test_conserva_el_nombre_y_la_documentacion(self):
        self.assertEqual(ServicioDePrueba.con_argumentos.__name__, "con_argumentos")
        self.assertIn("Suma", ServicioDePrueba.con_argumentos.__doc__)

    def test_conserva_la_firma_para_el_autocompletado(self):
        argumentos = list(inspect.signature(ServicioDePrueba.con_argumentos).parameters)
        self.assertEqual(argumentos, ["self", "uno", "dos", "tres"])

    def test_publica_los_roles_que_deja_pasar(self):
        self.assertEqual(
            ServicioDePrueba.medico_o_admin.roles_permitidos,
            (Roles.MEDICO, Roles.ADMINISTRADOR),
        )

    def test_con_todos_los_roles_publica_los_cuatro(self):
        """Lo que la ventana consulta para habilitar o no un boton."""
        self.assertEqual(
            ServicioDePrueba.cualquiera_que_ingreso.roles_permitidos, tuple(Roles)
        )

    def test_no_se_puede_decorar_sin_roles(self):
        with self.assertRaises(TypeError):
            autorizado()

    def test_no_se_puede_decorar_con_algo_que_no_es_un_rol(self):
        """Ni el texto del rol: una comparacion que nunca es cierta negaria
        a todo el mundo en silencio, que es mucho peor que reventar."""
        for basura in ("Médico", "Medico", "medico", 1, None):
            with self.subTest(basura=basura):
                with self.assertRaises(TypeError):
                    autorizado(basura)

    def test_avisa_si_el_objeto_no_trae_auth(self):
        with self.assertRaises(TypeError) as capturado:
            SinAuth().operacion()

        mensaje = str(capturado.exception)
        self.assertIn("auth", mensaje)
        self.assertIn("ServicioAutorizado", mensaje)

    def test_avisa_si_el_auth_no_es_un_auth(self):
        with self.assertRaises(TypeError):
            ConUnAuthFalso().operacion()


if __name__ == "__main__":
    unittest.main(verbosity=2)
