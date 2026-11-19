"""Pruebas de UsuarioRepositorio.

Es el unico repositorio cuya PK es TEXT (un uuid4().hex de 32 caracteres) y el
unico que agrega un metodo al contrato comun: `obtener_por_correo`, que es por
donde entra la autenticacion.
"""

import inspect
import sqlite3
import unittest

from model.constants import Roles
from model.repositories import UsuarioRepositorio, UsuarioSQLRepository
from model.usuario import Usuario

from .base import ContratoRepositorioMixin, RepositorioTestCase

HASH_DE_RELLENO = "$2b$12$" + "x" * 53


class UsuarioTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = UsuarioSQLRepository(self.db)

    def nuevo(self, **cambios) -> Usuario:
        n = self._siguiente()
        datos = {
            "id": f"{n:032d}",
            "hash_contrasena": HASH_DE_RELLENO,
            "correo": f"usuario{n}@hospital.com",
            "rol": "Médico",
        } | cambios
        return Usuario(**datos)


class ContratoDeUsuario(ContratoRepositorioMixin, UsuarioTestCase):
    """UsuarioRepositorio y su implementacion SQL."""

    interfaz = UsuarioRepositorio
    implementacion = UsuarioSQLRepository

    def test_la_interfaz_agrega_obtener_por_correo_al_contrato(self):
        """No esta en Repositorio: lo necesita la autenticacion."""
        self.assertTrue(UsuarioRepositorio.obtener_por_correo.__isabstractmethod__)
        self.assertFalse(
            getattr(
                UsuarioSQLRepository.obtener_por_correo, "__isabstractmethod__", False
            )
        )

    def test_obtener_por_correo_recibe_el_correo(self):
        argumentos = list(
            inspect.signature(UsuarioRepositorio.obtener_por_correo).parameters
        )
        self.assertEqual(argumentos, ["self", "correo"])


class RegistrarUsuario(UsuarioTestCase):
    """La llave la pone quien registra: es un uuid, no un autoincrement."""

    def test_respeta_el_id_que_trae_la_entidad(self):
        usuario = self.repo.registrar(self.nuevo(id="a" * 32))

        self.assertEqual(usuario.id, "a" * 32)
        self.assertIsNotNone(self.leer_fila("Usuario", id="a" * 32))

    def test_devuelve_la_misma_instancia(self):
        usuario = self.nuevo()
        self.assertIs(self.repo.registrar(usuario), usuario)

    def test_deja_la_fila_escrita_con_el_rol_como_texto(self):
        usuario = self.repo.registrar(self.nuevo(rol=Roles.ADMINISTRADOR))

        fila = self.leer_fila("Usuario", id=usuario.id)
        self.assertEqual(fila["rol"], "Administrador")
        self.assertEqual(fila["hash_contrasena"], HASH_DE_RELLENO)
        self.assertEqual(fila["activo"], 1, "un usuario nuevo nace activo")

    def test_guarda_el_booleano_activo_como_entero(self):
        usuario = self.repo.registrar(self.nuevo(activo=False))

        fila = self.leer_fila("Usuario", id=usuario.id)
        self.assertEqual(fila["activo"], 0)
        self.assertIsInstance(fila["activo"], int)

    def test_acepta_todos_los_roles_del_enum(self):
        """El CHECK del DDL y el enum Roles tienen que coincidir."""
        for rol in Roles:
            with self.subTest(rol=rol.value):
                self.repo.registrar(self.nuevo(rol=rol))

        self.assertEqual(self.contar("Usuario"), len(Roles))

    def test_el_correo_repetido_choca_con_el_unique(self):
        primero = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(correo=primero.correo))

    def test_el_id_repetido_choca_con_la_pk(self):
        primero = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(id=primero.id))

    def test_un_id_que_no_mide_32_no_pasa(self):
        with self.assertRaises(ValueError):
            self.nuevo(id="corto")

    def test_un_correo_mal_formado_no_pasa(self):
        with self.assertRaises(ValueError):
            self.nuevo(correo="esto-no-es-correo")

    def test_valida_la_entidad_antes_de_escribir(self):
        usuario = self.nuevo()
        usuario.correo = "sin-arroba"
        with self.assertRaises(ValueError):
            self.repo.registrar(usuario)
        self.assertEqual(self.contar("Usuario"), 0)


class ObtenerUsuarios(UsuarioTestCase):
    def test_obtener_por_id_reconstruye_la_entidad(self):
        usuario = self.repo.registrar(self.nuevo())

        leido = self.repo.obtener_por_id(usuario.id)

        self.assertIsInstance(leido, Usuario)
        self.assertEqual(leido.correo, usuario.correo)
        self.assertIs(leido.rol, Roles.MEDICO)
        self.assertIsInstance(leido.activo, bool)
        self.assertIs(leido.activo, True)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id("0" * 32))

    def test_obtener_por_correo_encuentra_al_usuario(self):
        usuario = self.repo.registrar(self.nuevo(correo="ana@hospital.com"))

        leido = self.repo.obtener_por_correo("ana@hospital.com")

        self.assertIsNotNone(leido)
        self.assertEqual(leido.id, usuario.id)

    def test_obtener_por_correo_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_correo("nadie@hospital.com"))

    def test_obtener_por_correo_distingue_mayusculas(self):
        """El SELECT compara tal cual; normalizar el correo le toca a Auth."""
        self.repo.registrar(self.nuevo(correo="ana@hospital.com"))

        self.assertIsNone(self.repo.obtener_por_correo("ANA@hospital.com"))

    def test_obtener_todos_ordena_por_id(self):
        self.repo.registrar(self.nuevo(id="c" * 32))
        self.repo.registrar(self.nuevo(id="a" * 32))
        self.repo.registrar(self.nuevo(id="b" * 32))

        ids = [u.id for u in self.repo.obtener_todos()]

        self.assertEqual(ids, ["a" * 32, "b" * 32, "c" * 32])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarUsuario(UsuarioTestCase):
    def test_inserta_cuando_el_id_es_nuevo(self):
        usuario = self.nuevo()

        self.assertTrue(self.repo.guardar(usuario))

        self.assertIsNotNone(self.repo.obtener_por_id(usuario.id))

    def test_actualiza_cuando_el_id_ya_existe(self):
        usuario = self.repo.registrar(self.nuevo())
        usuario.hash_contrasena = "$2b$12$" + "y" * 53

        self.assertTrue(self.repo.guardar(usuario))

        self.assertEqual(self.contar("Usuario"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(usuario.id).hash_contrasena,
            "$2b$12$" + "y" * 53,
        )

    def test_puede_cambiar_el_rol(self):
        usuario = self.repo.registrar(self.nuevo(rol=Roles.ENFERMERO))

        usuario.rol = Roles.ADMINISTRADOR
        self.assertTrue(self.repo.guardar(usuario))

        self.assertIs(self.repo.obtener_por_id(usuario.id).rol, Roles.ADMINISTRADOR)

    def test_valida_la_entidad_antes_de_escribir(self):
        usuario = self.repo.registrar(self.nuevo())
        usuario.rol = "Jefe"
        with self.assertRaises(ValueError):
            self.repo.guardar(usuario)


class DarBajaUsuario(UsuarioTestCase):
    """Baja logica: se le quita el acceso sin borrar la credencial."""

    def test_pone_activo_en_cero_sin_borrar_la_fila(self):
        usuario = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(usuario))

        self.assertEqual(self.contar("Usuario"), 1)
        self.assertEqual(self.leer_fila("Usuario", id=usuario.id)["activo"], 0)

    def test_refleja_la_baja_en_la_entidad(self):
        usuario = self.repo.registrar(self.nuevo())

        self.repo.darbaja(usuario)

        self.assertIs(usuario.activo, False)

    def test_el_usuario_sigue_siendo_consultable(self):
        """La credencial no desaparece: un admin tiene que poder verla."""
        usuario = self.repo.registrar(self.nuevo())

        self.repo.darbaja(usuario)

        leido = self.repo.obtener_por_id(usuario.id)
        self.assertIsNotNone(leido)
        self.assertIs(leido.activo, False)
        self.assertIsNotNone(self.repo.obtener_por_correo(usuario.correo))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id="0" * 32)))

    def test_funciona_con_un_usuario_ligado_a_una_persona(self):
        """Lo que antes era imposible: la FK es ON DELETE RESTRICT, pero esto no borra."""
        usuario = self.repo.registrar(self.nuevo())
        self.crear_derechohabiente(auth_user_id=usuario.id)

        self.assertTrue(self.repo.darbaja(usuario))

        self.assertEqual(self.leer_fila("Usuario", id=usuario.id)["activo"], 0)

    def test_dar_de_baja_dos_veces_es_inofensivo(self):
        usuario = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(usuario))
        self.assertTrue(self.repo.darbaja(usuario))
        self.assertIs(usuario.activo, False)

    def test_se_puede_reactivar_con_guardar(self):
        usuario = self.repo.registrar(self.nuevo())
        self.repo.darbaja(usuario)

        usuario.activo = True
        self.assertTrue(self.repo.guardar(usuario))

        self.assertIs(self.repo.obtener_por_id(usuario.id).activo, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
