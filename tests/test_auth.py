"""Pruebas de AuthService: registro, ingreso y la baja logica del usuario.

AuthService es el unico lugar donde vive politica de acceso, asi que lo que importa
aqui es que esa politica no se pueda esquivar y que no filtre informacion de
quien esta registrado.

Usa el repositorio SQL real contra la base en memoria, porque la regla de
`activo` cruza las dos capas.
"""

import unittest

import utils.autenticacion as modulo_auth
from model.constants import Roles
from model.repositories import UsuarioSQLRepository
from utils.autenticacion import AuthService, Sesion
from utils.sesion import SesionServicio
from utils.sesion_repositorio import SesionSQLRepositorio

from .base import RepositorioTestCase

CONTRASENA = "contrasena-valida-123"

_costo_real = None


def setUpModule():
    """Baja el costo de bcrypt mientras corren estas pruebas.

    En producción son 2^12 rondas (~0.35 s por hash) justamente para que atacar
    por fuerza bruta sea caro. Aquí se hashea decenas de veces y eso convertía
    este módulo en 19 segundos de los 20 de toda la suite. El 4 es el mínimo que
    acepta bcrypt; lo que se prueba es la lógica de Auth, no la dureza del hash,
    y el costo va anotado dentro de cada hash, así que `verificar` sigue
    funcionando igual.
    """
    global _costo_real
    _costo_real = modulo_auth.COSTO_BCRYPT
    modulo_auth.COSTO_BCRYPT = 4


def tearDownModule():
    modulo_auth.COSTO_BCRYPT = _costo_real


class ServicioSesionMemoria(SesionServicio):
    """Doble del servicio de sesion: guarda el token en memoria.

    Cumple el contrato pero sin llavero ni archivo. Las pruebas no deben tocar
    el llavero de quien las corre, y `SesionServicioArchivo` tampoco sirve
    aqui: apunta a un unico `sesion_prueba.txt` en la raiz que las 622 pruebas
    compartirian, pisandose el token entre ellas.

    Los tres metodos son de instancia y no de clase, al contrario que en los
    servicios de verdad, para que cada prueba arranque con su almacenamiento
    vacio; con estado de clase el token de una prueba sobreviviria a la
    siguiente. `crear` se hereda tal cual, que es justo lo que se quiere
    ejercitar.
    """

    def __init__(self) -> None:
        self.token: str | None = None

    def guardar(self, token: str) -> None:
        self.token = token

    def cargar(self) -> str | None:
        return self.token

    def limpiar(self) -> None:
        self.token = None


class AuthTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = UsuarioSQLRepository(self.db)
        self.sesiones = SesionSQLRepositorio(self.db, self.repo)
        self.servicio = ServicioSesionMemoria()
        self.auth = AuthService(self.repo, self.sesiones, self.servicio)

    def ingresar(self, **cambios) -> Sesion:
        """Ingreso de Ana, el de siempre. `recordar` se pasa por `cambios`."""
        return self.auth.ingresar("ana@hospital.com", CONTRASENA, **cambios)

    def caducar(self, sesion: Sesion) -> None:
        """Vence la sesion en la base, sin esperar las 8 horas.

        Se escribe el texto directo en la columna porque es el formato con el
        que `obtener_activa` compara (`fecha_expiracion > ?`, texto ISO UTC), y
        porque `Sesion` es un dataclass congelado: la fecha del objeto no se
        puede correr.
        """
        self.db.execute(
            "UPDATE sesiones SET fecha_expiracion = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", sesion.id),
        )

    def revocacion_de(self, sesion: Sesion) -> str | None:
        """La `fecha_revocacion` que quedo escrita, leida sin pasar por el repo."""
        return self.leer_fila("sesiones", id=sesion.id)["fecha_revocacion"]


class RegistrarUsuarios(AuthTestCase):
    def test_registra_y_devuelve_el_usuario_persistido(self):
        usuario = self.auth.registrar("ana@hospital.com", CONTRASENA, Roles.MEDICO)

        self.assertIsNotNone(self.repo.obtener_por_id(usuario.id))
        self.assertIs(usuario.rol, Roles.MEDICO)

    def test_un_usuario_nuevo_nace_activo(self):
        usuario = self.auth.registrar("ana@hospital.com", CONTRASENA, Roles.MEDICO)

        self.assertIs(usuario.activo, True)
        self.assertEqual(self.leer_fila("Usuario", id=usuario.id)["activo"], 1)

    def test_normaliza_el_correo(self):
        usuario = self.auth.registrar("  ANA@Hospital.COM ", CONTRASENA, Roles.MEDICO)

        self.assertEqual(usuario.correo, "ana@hospital.com")

    def test_nunca_guarda_la_contrasena_en_claro(self):
        usuario = self.auth.registrar("ana@hospital.com", CONTRASENA, Roles.MEDICO)

        guardado = self.leer_fila("Usuario", id=usuario.id)["hash_contrasena"]
        self.assertNotIn(CONTRASENA, guardado)
        self.assertTrue(guardado.startswith("$2b$"))

    def test_no_admite_dos_usuarios_con_el_mismo_correo(self):
        self.auth.registrar("ana@hospital.com", CONTRASENA, Roles.MEDICO)

        with self.assertRaises(ValueError):
            self.auth.registrar("ANA@hospital.com", CONTRASENA, Roles.ENFERMERO)

    def test_rechaza_una_contrasena_corta(self):
        with self.assertRaises(ValueError):
            self.auth.registrar("ana@hospital.com", "corta", Roles.MEDICO)

    def test_acepta_todos_los_roles(self):
        for n, rol in enumerate(Roles):
            with self.subTest(rol=rol.value):
                self.auth.registrar(f"u{n}@hospital.com", CONTRASENA, rol)


class IngresarAlSistema(AuthTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.usuario = self.auth.registrar(
            "ana@hospital.com", CONTRASENA, Roles.MEDICO
        )

    def test_abre_sesion_con_las_credenciales_correctas(self):
        sesion = self.auth.ingresar("ana@hospital.com", CONTRASENA)

        self.assertIsInstance(sesion, Sesion)
        self.assertEqual(sesion.usuario.id, self.usuario.id)
        self.assertIs(sesion.rol, Roles.MEDICO)

    def test_el_id_de_sesion_no_es_el_id_del_usuario(self):
        sesion = self.auth.ingresar("ana@hospital.com", CONTRASENA)

        self.assertNotEqual(sesion.id, self.usuario.id)

    def test_dos_ingresos_abren_sesiones_distintas(self):
        primera = self.auth.ingresar("ana@hospital.com", CONTRASENA)
        segunda = self.auth.ingresar("ana@hospital.com", CONTRASENA)

        self.assertNotEqual(primera.id, segunda.id)

    def test_el_correo_no_distingue_mayusculas_ni_espacios(self):
        self.assertIsNotNone(self.auth.ingresar("  ANA@Hospital.COM ", CONTRASENA))

    def test_rechaza_la_contrasena_equivocada(self):
        with self.assertRaises(ValueError):
            self.auth.ingresar("ana@hospital.com", "otra-contrasena")

    def test_rechaza_un_correo_que_no_existe(self):
        with self.assertRaises(ValueError):
            self.auth.ingresar("nadie@hospital.com", CONTRASENA)

    def test_el_mensaje_de_error_no_revela_si_el_correo_existe(self):
        """Mismo texto en los dos casos: si no, se pueden enumerar los usuarios."""
        with self.assertRaises(ValueError) as inexistente:
            self.auth.ingresar("nadie@hospital.com", CONTRASENA)
        with self.assertRaises(ValueError) as mala_contrasena:
            self.auth.ingresar("ana@hospital.com", "otra-contrasena")

        self.assertEqual(str(inexistente.exception), str(mala_contrasena.exception))


class UsuarioDadoDeBaja(AuthTestCase):
    """La baja logica del usuario tiene que cerrarle la puerta."""

    def setUp(self) -> None:
        super().setUp()
        self.usuario = self.auth.registrar(
            "ana@hospital.com", CONTRASENA, Roles.MEDICO
        )

    def test_un_usuario_desactivado_no_puede_entrar(self):
        self.repo.darbaja(self.usuario)

        with self.assertRaises(ValueError):
            self.auth.ingresar("ana@hospital.com", CONTRASENA)

    def test_el_error_es_el_mismo_que_con_una_contrasena_mala(self):
        """No se filtra que la cuenta existe pero esta desactivada."""
        self.repo.darbaja(self.usuario)

        with self.assertRaises(ValueError) as desactivado:
            self.auth.ingresar("ana@hospital.com", CONTRASENA)
        with self.assertRaises(ValueError) as inexistente:
            self.auth.ingresar("nadie@hospital.com", CONTRASENA)

        self.assertEqual(str(desactivado.exception), str(inexistente.exception))

    def test_desactivarlo_no_borra_su_credencial(self):
        self.repo.darbaja(self.usuario)

        self.assertEqual(self.contar("Usuario"), 1)
        self.assertIsNotNone(self.repo.obtener_por_correo("ana@hospital.com"))

    def test_reactivarlo_le_devuelve_el_acceso(self):
        self.repo.darbaja(self.usuario)

        self.usuario.activo = True
        self.repo.guardar(self.usuario)

        self.assertIsNotNone(self.auth.ingresar("ana@hospital.com", CONTRASENA))

    def test_un_usuario_ligado_a_una_persona_tambien_se_puede_desactivar(self):
        """Con el DELETE anterior esto era imposible: la FK lo bloqueaba."""
        self.crear_derechohabiente(auth_user_id=self.usuario.id)

        self.assertTrue(self.repo.darbaja(self.usuario))

        with self.assertRaises(ValueError):
            self.auth.ingresar("ana@hospital.com", CONTRASENA)


class CambiarContrasena(AuthTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.usuario = self.auth.registrar(
            "ana@hospital.com", CONTRASENA, Roles.MEDICO
        )

    def test_cambia_el_hash_y_persiste(self):
        viejo = self.usuario.hash_contrasena

        self.auth.cambiar_contrasena(self.usuario, CONTRASENA, "otra-contrasena-456")

        self.assertNotEqual(self.usuario.hash_contrasena, viejo)
        self.assertEqual(
            self.repo.obtener_por_id(self.usuario.id).hash_contrasena,
            self.usuario.hash_contrasena,
        )

    def test_despues_del_cambio_se_entra_con_la_nueva(self):
        self.auth.cambiar_contrasena(self.usuario, CONTRASENA, "otra-contrasena-456")

        self.assertIsNotNone(
            self.auth.ingresar("ana@hospital.com", "otra-contrasena-456")
        )
        with self.assertRaises(ValueError):
            self.auth.ingresar("ana@hospital.com", CONTRASENA)

    def test_exige_la_contrasena_vigente(self):
        with self.assertRaises(ValueError):
            self.auth.cambiar_contrasena(
                self.usuario, "no-es-la-actual", "otra-contrasena-456"
            )

    def test_no_acepta_una_contrasena_nueva_invalida(self):
        with self.assertRaises(ValueError):
            self.auth.cambiar_contrasena(self.usuario, CONTRASENA, "corta")


class RestaurarSesion(AuthTestCase):
    """Los tres caminos de guarda de `restaurar_sesion`, mas el camino sano.

    Es la unica entrada al sistema que no pide contrasena: acepta el token que
    quedo guardado en el dispositivo. Asi que lo que importa es que no acepte
    un token que ya no vale, y que cuando no vale no lo deje ahi tirado.
    """

    def setUp(self) -> None:
        super().setUp()
        self.usuario = self.auth.registrar(
            "ana@hospital.com", CONTRASENA, Roles.MEDICO
        )

    # ------------------------------------------------------------------
    # Camino sano: hay token y la sesion vive
    # ------------------------------------------------------------------

    def test_devuelve_la_sesion_que_se_guardo(self):
        sesion = self.ingresar(recordar=True)

        restaurada = self.auth.restaurar_sesion()

        self.assertIsNotNone(restaurada)
        self.assertEqual(restaurada.id, sesion.id)
        self.assertEqual(restaurada.usuario.id, self.usuario.id)
        self.assertIs(restaurada.rol, Roles.MEDICO)

    def test_restaurar_no_consume_el_token(self):
        """No es de un solo uso: la app puede restaurar en cada arranque."""
        sesion = self.ingresar(recordar=True)

        self.auth.restaurar_sesion()

        self.assertEqual(self.servicio.cargar(), sesion.token)
        self.assertIsNotNone(self.auth.restaurar_sesion())

    def test_la_sesion_sana_no_se_revoca_al_restaurarla(self):
        sesion = self.ingresar(recordar=True)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.revocacion_de(sesion))

    # ------------------------------------------------------------------
    # Caso 1: no hay token en el dispositivo
    # ------------------------------------------------------------------

    def test_sin_token_guardado_no_hay_sesion(self):
        self.assertIsNone(self.auth.restaurar_sesion())

    def test_ingresar_sin_recordar_no_deja_nada_que_restaurar(self):
        """`recordar` es explicito: sin el, la sesion no sobrevive al cierre."""
        self.ingresar()

        self.assertIsNone(self.auth.restaurar_sesion())

    # ------------------------------------------------------------------
    # Caso 2: hay token, pero la sesion ya no vale
    # ------------------------------------------------------------------

    def test_una_sesion_caducada_no_se_restaura(self):
        sesion = self.ingresar(recordar=True)
        self.caducar(sesion)

        self.assertIsNone(self.auth.restaurar_sesion())

    def test_una_sesion_caducada_se_borra_del_dispositivo(self):
        sesion = self.ingresar(recordar=True)
        self.caducar(sesion)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.servicio.cargar())

    def test_una_sesion_caducada_no_se_marca_como_revocada(self):
        """Vencerse no es cerrarse.

        `fecha_revocacion` es el dato que distingue 'alguien la cerro' de 'se
        vencio sola', y eso vale para una auditoria: no hay que mancharlo al
        limpiar el dispositivo.
        """
        sesion = self.ingresar(recordar=True)
        self.caducar(sesion)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.revocacion_de(sesion))

    def test_una_sesion_revocada_no_se_restaura(self):
        sesion = self.ingresar(recordar=True)
        self.sesiones.revocar(sesion)

        self.assertIsNone(self.auth.restaurar_sesion())

    def test_una_sesion_revocada_se_borra_del_dispositivo(self):
        sesion = self.ingresar(recordar=True)
        self.sesiones.revocar(sesion)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.servicio.cargar())

    def test_un_token_que_no_corresponde_a_nada_se_borra(self):
        """El caso de una base reinstalada, o de basura escrita a mano."""
        self.servicio.guardar("este-token-no-existe-en-la-base")

        self.assertIsNone(self.auth.restaurar_sesion())
        self.assertIsNone(self.servicio.cargar())

    # ------------------------------------------------------------------
    # Caso 3: la sesion vive, pero su dueno fue dado de baja
    # ------------------------------------------------------------------

    def test_un_usuario_dado_de_baja_no_restaura_su_sesion(self):
        """La baja logica no puede esperar a que la sesion venza sola.

        `ingresar` ya le cierra la puerta a un usuario inactivo; si
        `restaurar_sesion` no hiciera lo mismo, bastaria con no cerrar la app
        para seguir trabajando hasta ocho horas despues de la baja.
        """
        self.ingresar(recordar=True)
        self.repo.darbaja(self.usuario)

        self.assertIsNone(self.auth.restaurar_sesion())

    def test_dar_de_baja_borra_el_token_del_dispositivo(self):
        self.ingresar(recordar=True)
        self.repo.darbaja(self.usuario)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.servicio.cargar())

    def test_dar_de_baja_revoca_la_sesion_en_la_base(self):
        """Aqui si se revoca: la sesion seguia viva, la cerro una decision."""
        sesion = self.ingresar(recordar=True)
        self.repo.darbaja(self.usuario)

        self.auth.restaurar_sesion()

        self.assertIsNotNone(self.revocacion_de(sesion))

    def test_el_token_de_un_usuario_dado_de_baja_ya_no_abre_nada(self):
        sesion = self.ingresar(recordar=True)
        self.repo.darbaja(self.usuario)

        self.auth.restaurar_sesion()

        self.assertIsNone(self.sesiones.obtener_activa(sesion.token))

    def test_reactivar_al_usuario_no_revive_el_token_viejo(self):
        """Revocar es definitivo: para volver a entrar hay que dar la contrasena."""
        sesion = self.ingresar(recordar=True)
        self.repo.darbaja(self.usuario)
        self.auth.restaurar_sesion()

        self.usuario.activo = True
        self.repo.guardar(self.usuario)

        self.assertIsNone(self.sesiones.obtener_activa(sesion.token))


class CerrarSesion(AuthTestCase):
    """Cerrar sesion tiene que cerrar los dos lados: la base y el dispositivo."""

    def setUp(self) -> None:
        super().setUp()
        self.usuario = self.auth.registrar(
            "ana@hospital.com", CONTRASENA, Roles.MEDICO
        )
        self.sesion = self.ingresar(recordar=True)

    def test_devuelve_true_cuando_habia_una_sesion_abierta(self):
        self.assertTrue(self.auth.cerrar_sesion())

    def test_revoca_la_sesion_en_la_base(self):
        self.auth.cerrar_sesion()

        self.assertIsNotNone(self.revocacion_de(self.sesion))

    def test_borra_el_token_del_dispositivo(self):
        self.auth.cerrar_sesion()

        self.assertIsNone(self.servicio.cargar())

    def test_el_token_ya_no_abre_nada(self):
        self.auth.cerrar_sesion()

        self.assertIsNone(self.sesiones.obtener_activa(self.sesion.token))

    def test_despues_de_cerrar_no_hay_nada_que_restaurar(self):
        self.auth.cerrar_sesion()

        self.assertIsNone(self.auth.restaurar_sesion())

    def test_cerrar_dos_veces_devuelve_false_la_segunda(self):
        """Cerrar lo que ya esta cerrado no es un error, pero tampoco cierra nada."""
        self.assertTrue(self.auth.cerrar_sesion())
        self.assertFalse(self.auth.cerrar_sesion())

    def test_no_corre_la_hora_del_primer_cierre(self):
        """La hora que importa para una auditoria es la del cierre de verdad."""
        self.auth.cerrar_sesion()
        primera = self.revocacion_de(self.sesion)

        self.auth.cerrar_sesion()

        self.assertEqual(self.revocacion_de(self.sesion), primera)

    def test_sin_sesion_abierta_devuelve_false(self):
        self.auth.cerrar_sesion()
        self.servicio.limpiar()

        self.assertFalse(self.auth.cerrar_sesion())

    def test_un_token_muerto_se_limpia_aunque_no_haya_que_revocar(self):
        self.servicio.guardar("este-token-no-existe-en-la-base")

        self.assertFalse(self.auth.cerrar_sesion())
        self.assertIsNone(self.servicio.cargar())

    def test_con_una_sesion_explicita_cierra_esa_y_no_otra(self):
        otra = self.ingresar()

        self.assertTrue(self.auth.cerrar_sesion(otra))

        self.assertIsNone(self.sesiones.obtener_activa(otra.token))
        self.assertIsNotNone(self.revocacion_de(otra))
        self.assertIsNone(self.revocacion_de(self.sesion))


class HasheoDeContrasenas(unittest.TestCase):
    """No toca la base: solo las primitivas de bcrypt."""

    def test_el_mismo_texto_da_hashes_distintos(self):
        """bcrypt mete un salt nuevo en cada hash."""
        self.assertNotEqual(AuthService.hashear(CONTRASENA), AuthService.hashear(CONTRASENA))

    def test_los_dos_hashes_verifican_igual(self):
        for _ in range(2):
            self.assertTrue(AuthService.verificar(CONTRASENA, AuthService.hashear(CONTRASENA)))

    def test_rechaza_la_contrasena_equivocada(self):
        self.assertFalse(AuthService.verificar("otra", AuthService.hashear(CONTRASENA)))

    def test_verificar_no_revienta_con_basura(self):
        self.assertFalse(AuthService.verificar(CONTRASENA, "no-es-un-hash"))
        self.assertFalse(AuthService.verificar("", ""))

    def test_no_acepta_una_contrasena_mas_larga_que_el_limite_de_bcrypt(self):
        with self.assertRaises(ValueError):
            AuthService.hashear("x" * 73)


if __name__ == "__main__":
    unittest.main(verbosity=2)
