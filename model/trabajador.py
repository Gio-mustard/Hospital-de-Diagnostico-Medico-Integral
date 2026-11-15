"""Tabla Trabajador: especialización de DerechoHabiente."""

from datetime import date

from .constants import PATRON_NUMERO_EMPLEADO, Generos
from .derechohabiente import DerechoHabiente


class Trabajador(DerechoHabiente):
    """Derechohabiente contratado por el hospital.

    Es la clase padre de `Medico` y `Enfermero`, que en el DDL son tablas con
    un `id_trabajador NOT NULL UNIQUE`.
    """

    _CAMPOS_CLAVE = ('id_trabajador',)

    def __init__(
        self,
        *,
        id_trabajador: int | None = None,
        numero_empleado: str,
        departamento: str,
        fecha_ingreso: date | str,
        id_derechohabiente: int | None = None,
        nombres: str,
        apellido_paterno: str,
        apellido_materno: str | None = None,
        direccion_calle: str,
        codigo_postal: str,
        ciudad: str,
        estado: str,
        fecha_nacimiento: date | str,
        genero: Generos | str | None = None,
        telefono: str | None = None,
        curp: str,
        activo: bool = True,
        auth_user_id: str | None = None,
    ) -> None:
        super().__init__(
            id_derechohabiente=id_derechohabiente,
            nombres=nombres,
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            direccion_calle=direccion_calle,
            codigo_postal=codigo_postal,
            ciudad=ciudad,
            estado=estado,
            fecha_nacimiento=fecha_nacimiento,
            genero=genero,
            telefono=telefono,
            curp=curp,
            activo=activo,
            auth_user_id=auth_user_id,
        )
        self.id_trabajador = id_trabajador
        self.numero_empleado = numero_empleado
        self.departamento = departamento
        self.fecha_ingreso = fecha_ingreso

    @property
    def antiguedad_en_anios(self) -> int:
        ingreso: date = self.fecha_ingreso  # ya normalizado por la validación
        hoy = self._hoy()
        cumplio = (hoy.month, hoy.day) >= (ingreso.month, ingreso.day)
        return hoy.year - ingreso.year - (0 if cumplio else 1)

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_trabajador')
        self._validar_llave_foranea('id_derechohabiente', opcional=True)

        # chk_trab_num_emp
        self._validar_patron(
            'numero_empleado', PATRON_NUMERO_EMPLEADO, "'EMP-' y al menos 4 dígitos"
        )

        # chk_trab_departamento
        self._validar_texto('departamento', 100)

        # chk_trab_fecha_ing + trg_trab_fecha_ing_ins / _upd
        self._validar_fecha('fecha_ingreso', maxima=self._hoy())

        # Regla de congruencia que el DDL no puede expresar: nadie entra a
        # trabajar antes de nacer.
        if self.fecha_ingreso < self.fecha_nacimiento:
            self._fallar(
                'fecha_ingreso',
                self.fecha_ingreso,
                f"no puede ser anterior a la fecha de nacimiento ({self.fecha_nacimiento})",
            )
