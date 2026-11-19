"""Corredor de las pruebas: `python -m tests`.

Envuelve a `unittest` para que el resultado se lea de un vistazo: agrupa por
clase, marca cada prueba con su resultado y cierra con un resumen contado.

    ./env/bin/python -m tests              # todas
    ./env/bin/python -m tests cita         # solo las que mencionen "cita"
    ./env/bin/python -m tests -q           # solo el resumen
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

ANCHO = 72

VERDE = "\033[32m"
ROJO = "\033[31m"
AMARILLO = "\033[33m"
GRIS = "\033[90m"
NEGRITA = "\033[1m"
FIN = "\033[0m"


def _color(texto: str, color: str) -> str:
    """Pinta el texto solo si la salida es una terminal."""
    if not sys.stdout.isatty():
        return texto
    return f"{color}{texto}{FIN}"


class ResultadoLegible(unittest.TextTestResult):
    """Imprime una linea por prueba, agrupada bajo el nombre de su clase."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clase_actual = None

    def _encabezado(self, test) -> None:
        clase = test.__class__
        if clase is self._clase_actual:
            return
        self._clase_actual = clase
        titulo = (clase.__doc__ or clase.__name__).strip().splitlines()[0]
        self.stream.writeln("")
        self.stream.writeln(_color(f"  {clase.__name__}", NEGRITA))
        self.stream.writeln(_color(f"  {titulo}", GRIS))

    def _linea(self, test, marca: str, color: str, nota: str = "") -> None:
        self._encabezado(test)
        nombre = test._testMethodName.removeprefix("test_").replace("_", " ")
        texto = f"    {_color(marca, color)}  {nombre}"
        if nota:
            texto += _color(f"  ({nota})", GRIS)
        self.stream.writeln(texto)
        self.stream.flush()

    def addSuccess(self, test):
        super(unittest.TextTestResult, self).addSuccess(test)
        self._linea(test, "✓", VERDE)

    def addFailure(self, test, err):
        super(unittest.TextTestResult, self).addFailure(test, err)
        self._linea(test, "✗", ROJO, "falló la aserción")

    def addError(self, test, err):
        super(unittest.TextTestResult, self).addError(test, err)
        self._linea(test, "✗", ROJO, f"error: {err[0].__name__ if not err[0] is None else "[No se encontro el nombre del error]"}")

    def addSkip(self, test, reason):
        super(unittest.TextTestResult, self).addSkip(test, reason)
        self._linea(test, "–", AMARILLO, f"omitida: {reason}")

    def addExpectedFailure(self, test, err):
        super(unittest.TextTestResult, self).addExpectedFailure(test, err)
        self._linea(test, "!", AMARILLO, "falla esperada: defecto conocido")

    def addUnexpectedSuccess(self, test):
        super(unittest.TextTestResult, self).addUnexpectedSuccess(test)
        self._linea(test, "?", AMARILLO, "pasó, pero se esperaba que fallara")


def main() -> int:
    argumentos = [a for a in sys.argv[1:] if not a.startswith("-")]
    silencioso = "-q" in sys.argv or "--quiet" in sys.argv

    suite = unittest.TestLoader().discover(
        start_dir=str(RAIZ / "tests"), top_level_dir=str(RAIZ)
    )

    if argumentos:
        filtro = argumentos[0].lower()
        planas = [t for t in _aplanar(suite) if filtro in t.id().lower()]
        if not planas:
            print(_color(f"Ninguna prueba coincide con {filtro!r}.", ROJO))
            return 1
        suite = unittest.TestSuite(planas)
        print(f"Filtro: {filtro!r} -> {len(planas)} prueba(s)")

    print(_color("=" * ANCHO, GRIS))
    print(_color(f"  PRUEBAS  ·  {suite.countTestCases()} en total", NEGRITA))
    print(_color("=" * ANCHO, GRIS))

    # verbosity=1 a proposito: con 2, TextTestResult imprime ademas su propia
    # linea larga por prueba y se duplica todo. En 1 manda ResultadoLegible,
    # que tampoco saca los puntos porque sus addSuccess/addFailure saltan a
    # TestResult y se brincan a TextTestResult.
    corredor = unittest.TextTestRunner(
        resultclass=ResultadoLegible,
        verbosity=0 if silencioso else 1,
        stream=open("/dev/null", "w") if silencioso else sys.stdout,
        descriptions=False,
    )
    resultado = corredor.run(suite)

    _resumen(resultado)
    return 0 if resultado.wasSuccessful() else 1


def _aplanar(suite):
    """Recorre el arbol de suites y devuelve las pruebas una por una."""
    for elemento in suite:
        if isinstance(elemento, unittest.TestSuite):
            yield from _aplanar(elemento)
        else:
            yield elemento


def _resumen(resultado) -> None:
    corridas = resultado.testsRun
    fallos = len(resultado.failures)
    errores = len(resultado.errors)
    omitidas = len(resultado.skipped)
    esperados = len(resultado.expectedFailures)
    inesperados = len(resultado.unexpectedSuccesses)
    bien = corridas - fallos - errores - omitidas - esperados - inesperados

    print()
    print(_color("=" * ANCHO, GRIS))
    renglones = [
        ("pasaron", bien, VERDE),
        ("fallaron", fallos, ROJO),
        ("errores", errores, ROJO),
        ("fallas esperadas (defectos conocidos)", esperados, AMARILLO),
        ("pasaron sin esperarlo", inesperados, AMARILLO),
        ("omitidas", omitidas, AMARILLO),
    ]
    for etiqueta, cuenta, color in renglones:
        if cuenta:
            print(f"  {_color(f'{cuenta:3d}', color)}  {etiqueta}")

    print(_color("-" * ANCHO, GRIS))
    if resultado.wasSuccessful():
        print(_color(f"  TODO BIEN  ·  {corridas} prueba(s) corridas", VERDE + NEGRITA))
    else:
        print(
            _color(
                f"  HAY FALLOS  ·  {fallos + errores} de {corridas}", ROJO + NEGRITA
            )
        )
    print(_color("=" * ANCHO, GRIS))

    for titulo, casos in (("FALLOS", resultado.failures), ("ERRORES", resultado.errors)):
        if not casos:
            continue
        print()
        print(_color(f"{titulo}:", ROJO + NEGRITA))
        for test, traza in casos:
            print(f"\n  {_color(test.id(), NEGRITA)}")
            for linea in traza.strip().splitlines():
                print(f"    {linea}")


if __name__ == "__main__":
    sys.exit(main())
