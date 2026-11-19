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

        # Valida solo si no hay una hija construyendose (ver Entidad en constants.py).
        if type(self) is Medicamento:
            self._validar_propiedades()

    @property
    def agotado(self) -> bool:
        return self.stock == 0

    def _validar_propiedades(self) -> None:
        super()._validar_propiedades()
        self._validar_clave_propia('id_medicamento')

        self._validar_texto('nombre', 150)
        self._validar_texto('presentacion', 100)
        self._validar_texto('lote', 50)

        self._validar_entero('stock', minimo=0)

        self._validar_booleano('disponible')

        self._validar_fecha('caducidad', minima=self._hoy_mas(DIAS_MINIMOS_CADUCIDAD))
        self._validar_fecha('proximo_pedido', opcional=True)

        if self.stock == 0 and self.disponible:
            self._fallar(
                'disponible', self.disponible, "no puede ser True si el stock está en 0"
            )
