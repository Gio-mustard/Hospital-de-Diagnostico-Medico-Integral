"""Pruebas de Auth: registro, ingreso y la baja logica del usuario.

Auth es el unico lugar donde vive politica de acceso, asi que lo que importa
aqui es que esa politica no se pueda esquivar y que no filtre informacion de
quien esta registrado.

Usa el repositorio SQL real contra la base en memoria, porque la regla de
`activo` cruza las dos capas.
"""

import unittest

import utils.auth as modulo_auth
from model.constants import Roles
from model.repositories import UsuarioSQLRepository
from utils.auth import Auth, Sesion

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


class AuthTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = UsuarioSQLRepository(self.db)
        self.auth = Auth(self.repo)


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


class HasheoDeContrasenas(unittest.TestCase):
    """No toca la base: solo las primitivas de bcrypt."""

    def test_el_mismo_texto_da_hashes_distintos(self):
        """bcrypt mete un salt nuevo en cada hash."""
        self.assertNotEqual(Auth.hashear(CONTRASENA), Auth.hashear(CONTRASENA))

    def test_los_dos_hashes_verifican_igual(self):
        for _ in range(2):
            self.assertTrue(Auth.verificar(CONTRASENA, Auth.hashear(CONTRASENA)))

    def test_rechaza_la_contrasena_equivocada(self):
        self.assertFalse(Auth.verificar("otra", Auth.hashear(CONTRASENA)))

    def test_verificar_no_revienta_con_basura(self):
        self.assertFalse(Auth.verificar(CONTRASENA, "no-es-un-hash"))
        self.assertFalse(Auth.verificar("", ""))

    def test_no_acepta_una_contrasena_mas_larga_que_el_limite_de_bcrypt(self):
        with self.assertRaises(ValueError):
            Auth.hashear("x" * 73)


if __name__ == "__main__":
    unittest.main(verbosity=2)
