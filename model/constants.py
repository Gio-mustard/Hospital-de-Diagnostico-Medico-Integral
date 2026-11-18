"""Enums, patrones de validación y la clase raíz de todas las entidades.

Cada enum, cada patrón y cada límite de este módulo corresponde a un
CHECK o a un TRIGGER del DDL. 
"""

from abc import ABC, ABCMeta, abstractmethod
from datetime import date, datetime, timedelta
from enum import Enum
from json import JSONDecodeError, loads
from re import fullmatch
from typing import Any, ClassVar, NoReturn

# ---------------------------------------------------------------------------
# Enums: una por cada CHECK (... IN (...)) del DDL
# ---------------------------------------------------------------------------

class Roles(Enum):
    """Usuario.rol -> chk_usuario_rol"""

    ADMINISTRADOR = 'Administrador'
    RECEPCIONISTA = 'Recepcionista'
    MEDICO = 'Médico'
    ENFERMERO = 'Enfermero'

class Generos(Enum):
    """DerechoHabiente.genero -> chk_dh_genero"""

    MASCULINO = 'Masculino'
    FEMENINO = 'Femenino'
    OTRO = 'Otro'


class TiposSangre(Enum):
    """Paciente.tipo_sangre -> chk_paciente_sangre"""

    A_POSITIVO = 'A+'
    A_NEGATIVO = 'A-'
    B_POSITIVO = 'B+'
    B_NEGATIVO = 'B-'
    AB_POSITIVO = 'AB+'
    AB_NEGATIVO = 'AB-'
    O_POSITIVO = 'O+'
    O_NEGATIVO = 'O-'


class Turnos(Enum):
    """Recepcionista.turno -> chk_recep_turno"""

    MATUTINO = 'Matutino'
    VESPERTINO = 'Vespertino'
    NOCTURNO = 'Nocturno'
    GUARDIA = 'Guardia'


class TiposHabitacion(Enum):
    """Habitacion.tipo -> chk_hab_tipo"""

    INDIVIDUAL = 'Individual'
    DOBLE = 'Doble'
    PEDIATRIA = 'Pediatría'
    UCI = 'UCI'
    AISLAMIENTO = 'Aislamiento'


class EstadosHabitacion(Enum):
    """Habitacion.estado -> chk_hab_estado"""

    DISPONIBLE = 'Disponible'
    OCUPADA = 'Ocupada'
    MANTENIMIENTO = 'Mantenimiento'
    LIMPIEZA = 'Limpieza'


class EstadosConsultorio(Enum):
    """Consultorio.estado -> chk_cons_estado (ojo: 'Ocupado', no 'Ocupada')"""

    DISPONIBLE = 'Disponible'
    OCUPADO = 'Ocupado'
    MANTENIMIENTO = 'Mantenimiento'


class TiposDocumento(Enum):
    """HistorialMedico.tipo_documento -> chk_hist_tipo"""

    EXPEDIENTE_PDF = 'Expediente PDF'
    NOTA_EVOLUCION = 'Nota Evolución'
    RESUMEN_URGENCIAS = 'Resumen Urgencias'
    LABORATORIO = 'Laboratorio'
    IMAGENOLOGIA = 'Imagenología'
    SIGNOS_VITALES = 'Signos Vitales'


class EstadosCita(Enum):
    """Cita.estado -> chk_cita_estado"""

    PROGRAMADA = 'Programada'
    COMPLETADA = 'Completada'
    CANCELADA = 'Cancelada'
    NO_ASISTIO = 'No asistió'


class NivelesUrgencia(Enum):
    """IngresoEmergencia.nivel_urgencia -> chk_emergencia_nivel"""

    CRITICO = 'Crítico'
    ALTO = 'Alto'
    MEDIO = 'Medio'
    BAJO = 'Bajo'


# ---------------------------------------------------------------------------
# Patrones regex para validar campos antes de que lleguen a la BD: 
# ---------------------------------------------------------------------------


#: length = 5 y sin caracteres no numéricos
PATRON_CODIGO_POSTAL = r"\d{5}"

#: length = 18 y sin caracteres no válidos de CURP (mayúsculas, dígitos y H/M)
PATRON_CURP = r"[A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d"

#'+' + dígito 1-9 y 7 a 14 dígitos más (largo 9 a 16)
PATRON_TELEFONO = r"\+[1-9]\d{7,14}"

#: 'EMP-' + 4 dígitos como mínimo, con largo total de 8 a 20
PATRON_NUMERO_EMPLEADO = r"EMP-\d{4,16}"

#:  de 7 a 10 dígitos
PATRON_CEDULA_PROFESIONAL = r"\d{7,10}"

#:  -> 'https://' + algo sin espacios
PATRON_URL_HTTPS = r"https://\S+"

# ---------------------------------------------------------------------------
# Límites numéricos y de fechas
# ---------------------------------------------------------------------------


LONGITUD_UUID = 36 #? Esto podria eliminarse solo usando un validador de UUID, pero lo dejo para que el mensaje de error sea más claro y no diga "no es un UUID válido" sino "debe medir exactamente 36 caracteres"

#: fecha_nacimiento >= '1900-01-01'
FECHA_NACIMIENTO_MINIMA = date(1900, 1, 1)

#: Pisos del hospital, existen 20 pisos.
PISO_MINIMO = 1
PISO_MAXIMO = 20


DIAS_MINIMOS_CADUCIDAD = 15 # para medicamentos

CLAVES_TRATAMIENTO = ('diagnostico', 'medicamentos', 'indicaciones_generales')


# ---------------------------------------------------------------------------
# Clase raíz de los Modelos de la App
# ---------------------------------------------------------------------------


class _MetaEntidad(ABCMeta):
    """Metaclase que valida la entidad al terminar TODA la cadena de `__init__`.

    Sin esto cada entidad tendría que acordarse de llamar a
    `_validar_propiedades()` al final de su constructor, y hacerlo dentro del
    `__init__` de una clase padre tronaría: cuando corre `DerechoHabiente.__init__`
    los atributos propios de `Medico` todavía no existen.

    Al envolver la construcción, la validación corre una sola vez y hasta el
    final, así que un objeto inválido nunca llega a manos de quien lo construyó:
    el `ValueError` sale del constructor.
    """

    # -------------------
    # ! Quite este metodo porque me quitaba los errores de parametros de constructor en el editor, y no me daba un autocompletado util
    # ! Por lo mismo, cada entidad debera de llamar a _validar_propiedades() individualmente
    # -------------------

    # def __call__(cls, *args: Any, **kwargs: Any) -> Any:
    #     instancia = super().__call__(*args, **kwargs)
    #     instancia._validar_propiedades()
    #     return instancia


class Entidad(ABC, metaclass=_MetaEntidad):
    """Raíz abstracta de todas las entidades del dominio.

    Le da dos cosas a sus herederas:

    1. El contrato `_validar_propiedades()`, que traduce a Python los CHECK y
       los TRIGGER del DDL. Cada implementación arranca con
       `super()._validar_propiedades()`, así que las reglas del padre no se
       vuelven a escribir en la hija.
    2. Un juego de validadores reutilizables (`_validar_texto`, `_validar_enum`,
       `_validar_fecha`, ...). Las entidades declaran QUÉ validar y no CÓMO.
       De paso normalizan: un `'2004-05-17'` leído de SQLite queda como `date`
       y un `'Masculino'` queda como `Generos.MASCULINO`, de modo que el
       repositorio puede pasar los valores crudos de la fila sin convertirlos.
    """

    #: Atributos que forman la llave primaria, esto es mas que nada para los mensajes de error, NO deberia de usarse para obtener los id de una entidad.
    _CAMPOS_CLAVE: ClassVar[tuple[str, ...]] = ()


    @abstractmethod
    def _validar_propiedades(self) -> None:
        """Valida las restricciones del DDL para esta entidad.

        Nombre con un solo guion bajo a propósito: con dos (`__validar...`)
        Python aplica *name mangling* y el método de la hija se llamaría
        `_Hija__validar_propiedades`, con lo que no implementaría el método
        abstracto ni podría encadenarse con `super()`.

        es privado pue...
        """

    # -- identidad ---------------------------------------------------------

    @property
    def clave(self) -> Any:
        """Valor de la llave primaria: un escalar, o una tupla si es compuesta."""
        valores = tuple(getattr(self, campo, None) for campo in self._CAMPOS_CLAVE)
        if not valores:
            return None
        return valores[0] if len(valores) == 1 else valores

    def __repr__(self) -> str:
        campos = ", ".join(f"{nombre}={valor!r}" for nombre, valor in vars(self).items())
        return f"{type(self).__name__}({campos})"

    def __eq__(self, otro: object) -> bool:
        if type(otro) is not type(self):
            return NotImplemented
        clave = self.clave
        if clave is None:
            return self is otro
        return clave == otro.clave  # type: ignore[attr-defined]

    def __hash__(self) -> int:
        clave = self.clave
        return id(self) if clave is None else hash((type(self).__name__, clave))

    # -- apoyo para los validadores ----------------------------------------

    def _descripcion(self) -> str:
        clave = self.clave
        if clave is None:
            return f"{type(self).__name__} (sin id)"
        return f"{type(self).__name__} {clave}"

    def _fallar(self, campo: str, valor: Any, motivo: str) -> NoReturn:
        raise ValueError(
            f"El campo '{campo}' con valor {valor!r} en {self._descripcion()} "
            f"es inválido: {motivo}"
        )

    def _obtener(self, campo: str, opcional: bool) -> Any:
        """Devuelve el valor del campo, o `None` si es opcional y viene vacío."""
        valor = getattr(self, campo)
        if valor is None:
            if opcional:
                return None
            self._fallar(campo, valor, "es obligatorio (NOT NULL en el DDL)")
        return valor

    # -- validadores reutilizables -----------------------------------------

    def _validar_texto(self, campo: str, maximo: int, *, opcional: bool = False) -> None:
        """TEXT NOT NULL con un CHECK de `length(campo) <= maximo`."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if not isinstance(valor, str):
            self._fallar(campo, valor, "debe ser texto")
        if not valor.strip():
            self._fallar(campo, valor, "no puede estar vacío")
        if len(valor) > maximo:
            self._fallar(campo, valor, f"no puede pasar de {maximo} caracteres (tiene {len(valor)})")

    def _validar_patron(
        self, campo: str, patron: str, formato: str, *, opcional: bool = False
    ) -> None:
        """Campo de texto con un CHECK de GLOB, traducido a expresión regular."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if not isinstance(valor, str):
            self._fallar(campo, valor, "debe ser texto")
        if not fullmatch(patron, valor):
            self._fallar(campo, valor, f"no cumple el formato {formato}")

    def _validar_enum(
        self, campo: str, enumeracion: type[Enum], *, opcional: bool = False
    ) -> None:
        """CHECK de tipo `campo IN ('A', 'B', ...)`. Normaliza el texto al Enum."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if isinstance(valor, enumeracion):
            return
        try:
            setattr(self, campo, enumeracion(valor))
        except ValueError:
            permitidos = ", ".join(repr(miembro.value) for miembro in enumeracion)
            self._fallar(campo, valor, f"debe ser uno de: {permitidos}")

    def _validar_entero(
        self,
        campo: str,
        *,
        minimo: int | None = None,
        maximo: int | None = None,
        opcional: bool = False,
    ) -> None:
        """INTEGER con un CHECK de rango, como `piso BETWEEN 1 AND 20`."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if isinstance(valor, bool) or not isinstance(valor, int):
            self._fallar(campo, valor, "debe ser un número entero")
        if minimo is not None and valor < minimo:
            self._fallar(campo, valor, f"no puede ser menor que {minimo}")
        if maximo is not None and valor > maximo:
            self._fallar(campo, valor, f"no puede ser mayor que {maximo}")

    def _validar_booleano(self, campo: str) -> None:
        """BOOLEAN del DDL: INTEGER con CHECK (campo IN (0, 1)). Normaliza a bool."""
        valor = getattr(self, campo)
        if isinstance(valor, bool):
            return
        if valor in (0, 1):
            setattr(self, campo, bool(valor))
            return
        self._fallar(campo, valor, "debe ser True/False (0 o 1 en SQLite)")

    def _validar_clave_propia(self, campo: str) -> None:
        """Llave primaria AUTOINCREMENT: `None` mientras no se haya insertado."""
        self._validar_entero(campo, minimo=1, opcional=True)

    def _validar_llave_foranea(self, campo: str, *, opcional: bool = False) -> None:
        """FK a una llave primaria AUTOINCREMENT, que siempre arranca en 1."""
        self._validar_entero(campo, minimo=1, opcional=opcional)

    def _validar_fecha(
        self,
        campo: str,
        *,
        minima: date | None = None,
        maxima: date | None = None,
        opcional: bool = False,
    ) -> None:
        """DATE del DDL: TEXT 'YYYY-MM-DD'. Normaliza a `datetime.date`."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if isinstance(valor, datetime):
            valor = valor.date()
            setattr(self, campo, valor)
        elif isinstance(valor, str):
            try:
                valor = date.fromisoformat(valor)
            except ValueError:
                self._fallar(campo, valor, "debe tener el formato 'YYYY-MM-DD'")
            setattr(self, campo, valor)
        elif not isinstance(valor, date):
            self._fallar(campo, valor, "debe ser una fecha")
        if minima is not None and valor < minima:
            self._fallar(campo, valor, f"no puede ser anterior a {minima.isoformat()}")
        if maxima is not None and valor > maxima:
            self._fallar(campo, valor, f"no puede ser posterior a {maxima.isoformat()}")

    def _validar_fecha_hora(self, campo: str, *, opcional: bool = False) -> None:
        """TIMESTAMP del DDL: TEXT 'YYYY-MM-DD HH:MM:SS'. Normaliza a `datetime`."""
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if isinstance(valor, str):
            try:
                setattr(self, campo, datetime.fromisoformat(valor))
            except ValueError:
                self._fallar(campo, valor, "debe tener el formato 'YYYY-MM-DD HH:MM:SS'")
            return
        if not isinstance(valor, datetime):
            self._fallar(campo, valor, "debe ser una fecha con hora")

    def _validar_url_https(
        self, campo: str, *, maximo: int | None = None, opcional: bool = False
    ) -> None:
        """CHECK de URL: GLOB 'https://?*' y sin espacios ni saltos de línea."""
        if maximo is not None:
            self._validar_texto(campo, maximo, opcional=opcional)
        self._validar_patron(
            campo, PATRON_URL_HTTPS, "'https://' seguido de texto sin espacios", opcional=opcional
        )

    def _validar_json(
        self,
        campo: str,
        tipo: type[dict] | type[list],
        *,
        claves: tuple[str, ...] = (),
        opcional: bool = False,
    ) -> None:
        """JSONB del DDL: TEXT con `json_valid()` y `json_type()`.

        Acepta el objeto de Python ya armado o la cadena JSON tal como la
        devuelve SQLite, y deja el atributo siempre como `dict` o `list`.
        """
        valor = self._obtener(campo, opcional)
        if valor is None:
            return
        if isinstance(valor, str):
            try:
                valor = loads(valor)
            except JSONDecodeError as error:
                self._fallar(campo, valor, f"no es JSON válido ({error.msg})")
            setattr(self, campo, valor)
        if not isinstance(valor, tipo):
            esperado = "un objeto JSON" if tipo is dict else "un arreglo JSON"
            self._fallar(campo, valor, f"debe ser {esperado}")
        faltantes = [clave for clave in claves if clave not in valor]
        if faltantes:
            self._fallar(campo, valor, f"le faltan las llaves: {', '.join(faltantes)}")

    # -- utilidades para las reglas que dependen del día de hoy -------------

    @staticmethod
    def _hoy() -> date:
        """Equivalente a `date('now', 'localtime')` de los triggers del DDL."""
        return date.today()

    @staticmethod
    def _hoy_mas(dias: int) -> date:
        """Equivalente a `date('now', 'localtime', '+N days')`."""
        return date.today() + timedelta(days=dias)
