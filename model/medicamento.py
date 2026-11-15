"""Tabla Medicamento."""

from datetime import date

from .constants import DIAS_MINIMOS_CADUCIDAD, Entidad


class Medicamento(Entidad):
    """Medicamento en inventario."""

    _CAMPOS_CLAVE = ('id_medicamento',)

    def __init__(
        self,
        *,
        id_medicamento: int | None = None,
        nombre: str,
        presentacion: str,
        stock: int,
        lote: str,
        caducidad: date | str,
        disponible: bool,
        proximo_pedido: date | str | None = None,
    ) -> None:
        self.id_medicamento = id_medicamento
        self.nombre = nombre
        self.presentacion = presentacion
        self.stock = stock
        self.lote = lote
        self.caducidad = caducidad
        self.disponible = disponible
        self.proximo_pedido = proximo_pedido

    @property
    def agotado(self) -> bool:
        return self.stock == 0

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_medicamento')

        # chk_med_longitudes
        self._validar_texto('nombre', 150)
        self._validar_texto('presentacion', 100)
        self._validar_texto('lote', 50)

        # chk_med_stock
        self._validar_entero('stock', minimo=0)

        # chk_med_disponible
        self._validar_booleano('disponible')

        # chk_med_fechas + trg_medicamento_caducidad_ins / _upd
        self._validar_fecha('caducidad', minima=self._hoy_mas(DIAS_MINIMOS_CADUCIDAD))
        self._validar_fecha('proximo_pedido', opcional=True)

        # chk_med_stock_disponible: NOT (stock = 0 AND disponible = 1)
        if self.stock == 0 and self.disponible:
            self._fallar(
                'disponible', self.disponible, "no puede ser True si el stock está en 0"
            )
