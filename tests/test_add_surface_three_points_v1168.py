# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.168 (D101) — «Add Surface (three points)»: el modo existía, nadie lo
activaba.

``ToolMode.ADD_SURFACE_3PT`` llevaba ~98 versiones con miembro de
enumeración, cursor y texto de estado, y ningún ``_set_tool`` del
repositorio lo activaba. Con él, una traducción huérfana y
``SlipCircle.from_three_points`` ejercitada sólo por ``test_slip2d.py``.
Regla 3 en su forma pura: una función que el usuario no puede alcanzar.

QUÉ PROTEGE CADA BLOQUE, y qué pasa contra el árbol de 0.1.167:

  ROJO (mide el defecto)
    - la acción existe, se alcanza desde el menú y entra en el modo;
    - tres clics construyen el círculo y lo dejan en ``user_surfaces``;
    - el lienzo RECHAZA un trío que el motor habría aceptado en silencio;
    - un clic pendiente de otro modo ya no se cuela como primero de tres;
    - el texto de estado del modo sale traducido.

  VERDE por CONSERVACIÓN (identidades que el cambio no puede romper)
    - el motor no se mueve: sigue aceptando los tríos casi alineados y
      rechazando sólo la colinealidad exacta;
    - los cinco modos de 2 clics siguen funcionando de punta a punta;
    - terminar una frontera sigue funcionando, y el segundo Esc sale;
    - re-armar el MISMO modo conserva el clic pendiente.

Las dos cosas que este archivo NO hace, a propósito:

  - **no fija ningún factor de seguridad**. Lo que se comprueba son
    identidades y nombres: el círculo que aparece en el proyecto es, bit a
    bit, el que ``from_three_points`` devuelve con los mismos puntos de
    escena. Una instantánea de la aritmética de hoy no protegería nada;
  - **no juzga si el radio es sensato**. La guarda del lienzo es una regla
    de RESOLUCIÓN DE PANTALLA: rechaza lo que el ratón no puede expresar,
    no lo que a un geotécnico le parecería grande. Un círculo de 667 m es
    una rotura casi plana perfectamente legítima, y hay un test que exige
    que se acepte.

Los clics se escriben en PÍXELES enteros y los puntos de escena se derivan
de esos mismos píxeles: la regla es de píxeles, y ``mousePressEvent``
redondea con ``.toPoint()``. Y con el snapping APAGADO, porque
``_snap_point`` mete ``_draw_points`` como pseudo-frontera para cualquier
modo, de modo que con él encendido el test mediría el motor de snapping en
vez de la guarda.

Regla 5: el runner NO llama a ``setup_method``/``teardown_method``, y la
ventana está cacheada entre tests. Todo estado global —idioma, snapping,
transformada, tipo de superficie, modo, superficies, fronteras— se
restaura en ``finally``.
"""
from __future__ import annotations

import ast
import contextlib
import math
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402  (el simulado del runner)

try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QKeyEvent, QMouseEvent, QTransform
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WINDOWS: list = []

_KEY = "surf_three_points"
_LABEL = "Add Surface (three points)"
_HINT = "Click three points to define a circular surface"
_REFUSAL = ("Those three points are too close to a straight line to define "
            "a circle. Click a third point further from the line through "
            "the first two.")

# Medido por AST sobre TODA llamada a set_tool_mode/_set_tool de `ogr_gui`.
# La única forma de llamada que no nombra un ToolMode literal es el propio
# reenviador `_set_tool(mode)`, así que el censo es completo.
_NEVER_ENTERED = {
    # Andamiaje puro: cursor y texto de estado, y nadie los lee siquiera.
    "MEASURE", "ADD_SURFACE_CR",
    # Éstos SÍ los lee `_on_boundary_clicked`, pero como nadie entra en
    # ellos esas ramas `elif` son inalcanzables. La función en sí se
    # alcanza por otro camino: sus acciones están en el menú.
    "SCALE_BOUNDARY", "ROTATE_BOUNDARY", "EXPAND_SHRINK",
    "CHANGE_SLOPE_ANGLE",
}

# Los textos de estado de ToolMode NO los ve el escáner AST de
# test_i18n_coverage_v141, porque `set_tool_mode` llama a `tr()` con una
# VARIABLE. El techo de abajo es lo único que los mide.
_HINTS_TOTAL = 34
_HINTS_WITHOUT_SPANISH = 33


def _window():
    if _WINDOWS:
        return _WINDOWS[0]
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    # ANTES de construir: `_mk` traduce una sola vez, al construir.
    set_language("en")
    w = MainWindow()
    _WINDOWS.append(w)
    return w


@contextlib.contextmanager
def _canvas_ready(ppu: float = 20.0):
    """Lienzo con tamaño, zoom conocido y sin snapping, todo restaurado."""
    from ogr_gui.canvas.tool_mode import ToolMode
    w = _window()
    c = w.canvas
    prev = (c.snap_settings.snap, c.transform(), c.tool_mode,
            list(w.project.user_surfaces), w.project.is_dirty,
            list(w.project.boundaries))
    try:
        c.resize(800, 600)
        c.show()
        c.snap_settings.snap = False
        c.setTransform(QTransform().scale(ppu, -ppu))
        c._draw_points.clear()
        c._clear_draw_preview()
        w.project.user_surfaces.clear()
        yield w, c
    finally:
        c._draw_points.clear()
        c._clear_draw_preview()
        c.set_tool_mode(ToolMode.SELECT)
        (c.snap_settings.snap, tf, _mode, surf, dirty, bnds) = prev
        c.setTransform(tf)
        w.project.user_surfaces[:] = surf
        w.project.boundaries[:] = bnds
        w.project.is_dirty = dirty


@contextlib.contextmanager
def _messages(canvas):
    """Recoge lo que el lienzo manda a la barra de estado."""
    got: list = []
    canvas.status_message.connect(got.append)
    try:
        yield got
    finally:
        try:
            canvas.status_message.disconnect(got.append)
        except (TypeError, RuntimeError):  # pragma: no cover
            pass


def _press(canvas, px: int, py: int) -> None:
    """Un clic izquierdo en píxeles ENTEROS del viewport."""
    ev = QMouseEvent(QEvent.MouseButtonPress, QPointF(px, py),
                     canvas.mapToGlobal(QPoint(px, py)),
                     Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    canvas.mousePressEvent(ev)


def _key(canvas, key) -> None:
    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))


def _scene(canvas, px: int, py: int):
    """Lo que ``mousePressEvent`` verá para ese píxel. Mismo redondeo."""
    p = canvas.mapToScene(QPoint(px, py))
    return (p.x(), p.y())


def _menu_texts(window, name: str) -> list:
    """Etiquetas de un menú y de sus submenús.

    Devuelve una LISTA de textos y nunca un ``QMenu``: sostener el
    envoltorio de un menú más allá del bucle que lo produjo sobrevive al
    objeto C++ («Internal C++ object (QMenu) already deleted»).
    """
    out: list = []
    for act in window.menuBar().actions():
        sub = act.menu()
        if sub is None or act.text().replace("&", "") != name:
            continue
        for a in sub.actions():
            inner = a.menu()
            if inner is not None:
                out.extend(b.text() for b in inner.actions() if b.text())
            elif a.text():
                out.append(a.text())
    return out


def _activated_modes() -> set:
    """Modos que alguna llamada de `ogr_gui` llega a activar, por AST."""
    seen = set()
    for f in (_ROOT / "ogr_gui").rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Call)
                    and getattr(n.func, "attr", None) in ("set_tool_mode",
                                                          "_set_tool")
                    and n.args):
                continue
            a = n.args[0]
            if (isinstance(a, ast.Attribute)
                    and isinstance(a.value, ast.Name)
                    and a.value.id == "ToolMode"):
                seen.add(a.attr)
    return seen


# ======================================================================
@_requires_qt
class TestTheActionExistsAndIsReachable:
    """Regla 3: lo que no está en un menú no existe para el usuario."""

    def test_the_action_is_registered(self):
        assert _KEY in _window()._actions

    def test_its_label_is_the_orphan_translation(self):
        """El rótulo NO lleva puntos suspensivos, y no es un detalle.

        v0.1.166 midió la convención: «...» aparece sólo cuando se abre un
        diálogo, y ésta entra en modo de dibujo. Al ir sin ellos la clave
        casa con la entrada que llevaba huérfana desde 0.1.157 — con los
        puntos, `tr()` caería al inglés en silencio, que es exactamente el
        defecto «Add Grid»/«Add Grid...» que aquella versión encontró.
        """
        from ogr_gui.i18n import _DICTS
        act = _window()._actions[_KEY]
        assert act.text() == _LABEL
        assert not act.text().endswith("...")
        assert _LABEL in _DICTS["es"]

    def test_it_is_reachable_from_the_surfaces_menu(self):
        assert _LABEL in _menu_texts(_window(), "Surfaces")

    def test_it_sits_next_to_the_action_that_types_the_same_object(self):
        texts = _menu_texts(_window(), "Surfaces")
        i = texts.index(_LABEL)
        assert texts[i - 1] == "Add Surface (centre and radius)..."

    def test_no_label_in_the_menu_prefixes_another(self):
        """CONSERVADA. La invariante de D102, que esta acción podría haber
        roto: «Add Surface (three points)» y «Add Surface (centre and
        radius)...» divergen en «(t» / «(c», así que ninguna prefija a la
        otra. Un «Add Surface» a secas sí lo haría."""
        texts = _menu_texts(_window(), "Surfaces")
        pairs = [(a, b) for a in texts for b in texts
                 if a != b and b.startswith(a)]
        assert not pairs, pairs

    def test_it_carries_no_icon_and_the_old_key_stays_buried(self):
        """`surface_3pts` describía ESTE modo, y v0.1.166 la retiró del
        catálogo dejando un test que fija su ausencia. Re-añadirla lo
        pondría rojo; la acción va sin icono, como su hermana."""
        from ogr_gui.resources.icons import has
        assert _window()._actions[_KEY].icon().isNull()
        assert not has("surface_3pts")


@_requires_qt
class TestTheActionEntersTheMode:
    """El rótulo atado al COMPORTAMIENTO, no a otra cadena."""

    def test_triggering_it_enters_add_surface_3pt(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            assert c.tool_mode is ToolMode.ADD_SURFACE_3PT

    def test_it_follows_the_surface_type(self):
        """Deshabilitada fuera de circular, como su hermana: una corrida
        lleva UN tipo de superficie y un círculo no lo analiza una no
        circular."""
        from ogr_core.project.settings import SurfaceType
        w = _window()
        search = w.project.settings.search
        prev = search.surface_type
        try:
            search.surface_type = SurfaceType.CIRCULAR.value
            w.refresh_action_availability()
            assert w._actions[_KEY].isEnabled()
            search.surface_type = SurfaceType.NON_CIRCULAR.value
            w.refresh_action_availability()
            assert not w._actions[_KEY].isEnabled()
        finally:
            search.surface_type = prev
            w.refresh_action_availability()

    def test_the_tooltip_is_the_one_its_sibling_already_had(self):
        """Comparte las DOS ramas con `surf_centre_radius`: una segunda
        frase para la misma precondición es cómo un tooltip acaba
        contradiciendo al de al lado."""
        w = _window()
        w.refresh_action_availability()
        assert (w._actions[_KEY].toolTip()
                == w._actions["surf_centre_radius"].toolTip())


@_requires_qt
class TestThreeClicksMakeACircle:
    """El camino entero, con eventos de ratón de verdad."""

    def test_the_first_two_clicks_add_nothing(self):
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 100)
            _press(c, 400, 120)
            assert len(c._draw_points) == 2
            assert w.project.user_surfaces == []

    def test_the_third_click_appends_exactly_one(self):
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 100)
            _press(c, 400, 120)
            _press(c, 250, 400)
            assert len(w.project.user_surfaces) == 1

    def test_the_circle_is_the_circumcircle_of_those_scene_points(self):
        """IDENTIDAD entre dos caminos, no una captura: el círculo que
        aparece en el proyecto es el que ``from_three_points`` devuelve con
        los mismos tres puntos de escena. Si la aritmética del motor
        cambiara mañana, este test sigue siendo cierto — y debe serlo,
        porque lo que mide es el cableado, no la fórmula."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import SlipCircle
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            px = [(100, 100), (400, 120), (250, 400)]
            ref = SlipCircle.from_three_points(
                *[Vertex(*_scene(c, x, y)) for x, y in px])
            for x, y in px:
                _press(c, x, y)
            got = w.project.user_surfaces[-1]
            assert got.centre_x == ref.centre_x
            assert got.centre_y == ref.centre_y
            assert got.radius == ref.radius

    def test_it_returns_to_select_and_marks_the_project_dirty(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            w.project.is_dirty = False
            w._actions[_KEY].trigger()
            for x, y in ((100, 100), (400, 120), (250, 400)):
                _press(c, x, y)
            assert c.tool_mode is ToolMode.SELECT
            assert w.project.is_dirty

    def test_the_pending_points_and_the_preview_are_cleared(self):
        """Se limpia ANTES de emitir: el slot llama a ``refresh_scene()``,
        que vacía la escena, y un item de vista previa todavía guardado
        aquí sería un envoltorio C++ muerto."""
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            for x, y in ((100, 100), (400, 120), (250, 400)):
                _press(c, x, y)
            assert c._draw_points == []
            assert c._draw_preview_items == []

    def test_the_circle_reaches_the_scene(self):
        """El slot refrescó de verdad: 0.1.157 dibuja la superficie del
        usuario como círculo entero más marca de centro."""
        with _canvas_ready() as (w, c):
            c.refresh_scene()
            before = len(c.scene().items())
            w._actions[_KEY].trigger()
            for x, y in ((100, 100), (400, 120), (250, 400)):
                _press(c, x, y)
            assert len(c.scene().items()) > before

    def test_the_circle_is_manageable_like_any_other(self):
        """``_manage_user_surfaces`` trabaja sobre la lista por
        referencia, así que no hizo falta tocarlo — y eso se comprueba,
        no se supone."""
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            for x, y in ((100, 100), (400, 120), (250, 400)):
                _press(c, x, y)
            assert w._actions["surf_manage"].isEnabled()
            w.project.user_surfaces.clear()
            assert w.project.user_surfaces == []


@_requires_qt
class TestEscapeCancels:

    def test_escape_after_two_clicks_clears_them_and_stays_in_the_mode(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 100)
            _press(c, 400, 120)
            _key(c, Qt.Key_Escape)
            assert c._draw_points == []
            assert c.tool_mode is ToolMode.ADD_SURFACE_3PT
            assert w.project.user_surfaces == []

    def test_a_second_escape_leaves_the_mode(self):
        """CONSERVADA: ``keyPressEvent`` mira si hay puntos pendientes y no
        en qué modo está, así que un modo de 3 clics no necesitó tocarlo."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 100)
            _key(c, Qt.Key_Escape)
            _key(c, Qt.Key_Escape)
            assert c.tool_mode is ToolMode.SELECT


class TestTheEngineAcceptsWhatTheEyeCannot:
    """La evidencia de la regla 6, y el motor que NO se mueve.

    ``from_three_points`` compara ``abs(d) < 1e-14`` siendo ``d`` cuatro
    veces el área con signo: una tolerancia ABSOLUTA sobre una magnitud de
    área, que es lo que AGENTS.md prohíbe. Sólo salta con colinealidad
    exacta en coma flotante — lo único que un ratón nunca produce.
    """

    def test_a_near_collinear_trio_gives_a_kilometre_scale_circle(self):
        """Y la comprobación es una IDENTIDAD, no tres instantáneas: para
        esta configuración el radio es inversamente proporcional a la
        separación, así que ``r·ε`` es constante."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import SlipCircle
        productos = []
        for eps in (1e-3, 1e-6, 1e-9):
            c = SlipCircle.from_three_points(
                Vertex(0.0, 0.0), Vertex(10.0, 0.0), Vertex(20.0, eps))
            assert c.radius > 1.0 / eps
            productos.append(c.radius * eps)
        assert productos[0] == pytest.approx(productos[-1], rel=1e-2)

    def test_the_engine_only_refuses_exact_collinearity(self):
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import SlipCircle
        with pytest.raises(ValueError):
            SlipCircle.from_three_points(
                Vertex(0.0, 0.0), Vertex(10.0, 0.0), Vertex(20.0, 0.0))
        # A un nanómetro de la recta ya no protesta.
        SlipCircle.from_three_points(
            Vertex(0.0, 0.0), Vertex(10.0, 0.0), Vertex(20.0, 1e-9))

    def test_a_near_duplicate_pair_is_not_degenerate(self):
        """Por qué NO hay guarda de separación entre clics: dos puntos casi
        pegados con el tercero lejos dan un círculo perfectamente
        condicionado. La degeneración la gobierna la alineación."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import SlipCircle
        c = SlipCircle.from_three_points(
            Vertex(0.0, 0.0), Vertex(1e-8, 0.0), Vertex(10.0, 10.0))
        assert c.radius == pytest.approx(10.0, rel=1e-6)
        assert c.centre_y == pytest.approx(10.0, rel=1e-6)


@_requires_qt
class TestTheCanvasRefusesWhatTheEngineWouldAccept:
    """La guarda que el motor no tiene."""

    def test_the_segment_distance_helper_is_the_wrong_measure(self):
        """Contra quien «simplifique» reutilizando el ayudante que ya
        existe: recorta la proyección al segmento, así que con tres puntos
        EXACTAMENTE alineados y el tercero más allá del extremo contesta
        10 donde la perpendicular a la recta es 0."""
        from ogr_gui.canvas.canvas_view import _point_segment_distance
        assert _point_segment_distance(20, 0, 0, 0, 10, 0) == 10.0

    def test_one_pixel_off_the_line_is_refused_though_the_engine_accepts(self):
        """El hallazgo entero en un test: el lienzo rechaza un trío que el
        motor construye sin protestar, y con radio kilométrico."""
        from ogr_core.geometry import Vertex
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_slip2d.surface import SlipCircle
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            with _messages(c) as got:
                _press(c, 100, 300)
                _press(c, 500, 300)
                _press(c, 300, 301)
                assert w.project.user_surfaces == []
                assert len(c._draw_points) == 2
                assert c.tool_mode is ToolMode.ADD_SURFACE_3PT
                assert any(m == _REFUSAL for m in got)
            # Y el motor, con esos mismos tres puntos, contesta un círculo.
            libre = SlipCircle.from_three_points(
                *[Vertex(*_scene(c, x, y))
                  for x, y in ((100, 300), (500, 300), (300, 301))])
            assert libre.radius > 500.0

    def test_three_pixels_off_the_line_is_accepted(self):
        """El control que impide que la guarda sea un rechazo en bloque:
        sin él, ``return True`` pasaría todo lo demás de esta clase. A este
        zoom son 0,15 m y un radio de cientos de metros — una rotura casi
        plana perfectamente legítima."""
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 300)
            _press(c, 500, 300)
            _press(c, 300, 303)
            assert len(w.project.user_surfaces) == 1

    def test_a_third_click_exactly_on_the_line_keeps_the_first_two(self):
        """Rechazar no es reiniciar: dos clics buenos ya están invertidos y
        sus puntos rojos siguen en pantalla, que es lo que hace la
        corrección directa. Y deja estado POSITIVO que un test puede mirar,
        a diferencia de un reinicio, indistinguible de no haber pinchado."""
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 100, 300)
            _press(c, 500, 300)
            _press(c, 300, 300)
            assert len(c._draw_points) == 2
            assert w.project.user_surfaces == []
            # Y desde ahí un tercer clic bueno todavía cierra el círculo.
            _press(c, 300, 400)
            assert len(w.project.user_surfaces) == 1

    def test_the_two_base_points_cannot_be_the_same_click(self):
        """Con ``a == b`` no hay recta de la que alejarse, y cada clic
        posterior se rechazaría: sería un callejón sin salida del que sólo
        saca Esc. Se ignora el repetido, como cualquier clic que no acierta
        nada."""
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            _press(c, 200, 200)
            _press(c, 200, 200)
            assert len(c._draw_points) == 1

    def test_the_refusal_message_is_translated(self):
        from ogr_gui.i18n import _DICTS, set_language
        assert _REFUSAL in _DICTS["es"]
        with _canvas_ready() as (w, c):
            try:
                set_language("es")
                w._actions[_KEY].trigger()
                with _messages(c) as got:
                    _press(c, 100, 300)
                    _press(c, 500, 300)
                    _press(c, 300, 300)
                assert any(m == _DICTS["es"][_REFUSAL] for m in got)
                assert not any(m == _REFUSAL for m in got)
            finally:
                set_language("en")


@_requires_qt
class TestTheToleranceIsOnScreenAndNotInMetres:

    def test_the_same_pixels_decide_the_same_at_two_zooms(self):
        """AGENTS.md: las tolerancias de pantalla van en píxeles. El mismo
        patrón de píxeles a dos zooms da el MISMO veredicto aunque la
        perpendicular en unidades de modelo difiera diez veces — y esto se
        pone rojo el día que alguien escriba el umbral en metros."""
        perps = []
        for ppu in (20.0, 200.0):
            with _canvas_ready(ppu=ppu) as (w, c):
                (x0, y0), (x1, y1) = _scene(c, 100, 300), _scene(c, 500, 300)
                (xc, yc) = _scene(c, 300, 301)
                den = math.hypot(x1 - x0, y1 - y0)
                perps.append(abs((x1 - x0) * (yc - y0)
                                 - (y1 - y0) * (xc - x0)) / den)

                w._actions[_KEY].trigger()
                _press(c, 100, 300)
                _press(c, 500, 300)
                _press(c, 300, 301)          # 1 px: rechazado a los dos
                assert w.project.user_surfaces == []
                _press(c, 300, 303)          # 3 px: aceptado a los dos
                assert len(w.project.user_surfaces) == 1
        assert perps[0] == pytest.approx(10.0 * perps[1], rel=1e-6)


@_requires_qt
class TestSetToolModeDiscardsPendingClicks:
    """v0.1.168 (B): un clic pendiente no sobrevive a un cambio de
    herramienta. Era pre-existente y alcanzaba ya a los cinco modos de dos
    clics; el modo nuevo lo heredaba."""

    def test_a_pending_click_does_not_become_the_first_of_three(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            c.set_tool_mode(ToolMode.PICK_GRID_RECT)
            _press(c, 50, 50)
            assert len(c._draw_points) == 1
            w._actions[_KEY].trigger()
            assert c._draw_points == []
            _press(c, 100, 100)
            _press(c, 400, 120)
            # Con la fuga, estos dos habrían sido el segundo y el tercero.
            assert len(c._draw_points) == 2
            assert w.project.user_surfaces == []

    def test_the_two_click_modes_still_work_end_to_end(self):
        """CONSERVADA, y es la guarda contra perturbar los cinco modos: la
        rama nueva no toca una coma de su tupla."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            got: list = []
            c.segment_picked.connect(lambda *a: got.append(a))
            try:
                c.set_tool_mode(ToolMode.PICK_GRID_RECT)
                _press(c, 120, 130)
                _press(c, 420, 430)
                assert len(got) == 1
                assert got[0] == _scene(c, 120, 130) + _scene(c, 420, 430)
            finally:
                try:
                    c.segment_picked.disconnect()
                except (TypeError, RuntimeError):  # pragma: no cover
                    pass

    def test_setting_the_same_mode_twice_keeps_the_pending_click(self):
        """CONSERVADA, y deliberada: Pick Grid Rectangle se re-arma desde
        un diálogo que sigue abierto, así que re-entrar en el MISMO modo no
        puede ser una cancelación encubierta."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            c.set_tool_mode(ToolMode.PICK_GRID_RECT)
            _press(c, 80, 80)
            c.set_tool_mode(ToolMode.PICK_GRID_RECT)
            assert len(c._draw_points) == 1

    def test_a_boundary_in_progress_is_discarded_by_a_tool_change(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            c.set_tool_mode(ToolMode.DRAW_EXTERNAL)
            for x, y in ((100, 100), (300, 100), (300, 300)):
                _press(c, x, y)
            assert len(c._draw_points) == 3
            c.set_tool_mode(ToolMode.PAN)
            assert c._draw_points == []

    def test_finishing_a_boundary_still_works(self):
        """CONSERVADA: ``_finish_drawing`` vacía los puntos ANTES de pedir
        SELECT, así que el bloque nuevo es un no-op ahí."""
        from ogr_gui.canvas.tool_mode import ToolMode
        with _canvas_ready() as (w, c):
            got: list = []
            c.boundary_drawn.connect(got.append)
            try:
                c.set_tool_mode(ToolMode.DRAW_EXTERNAL)
                for x, y in ((100, 100), (400, 100), (400, 400), (100, 400)):
                    _press(c, x, y)
                _key(c, Qt.Key_Return)
                assert len(got) == 1
                assert len(got[0].polyline.vertices) == 4
                assert c.tool_mode is ToolMode.SELECT
            finally:
                try:
                    c.boundary_drawn.disconnect(got.append)
                except (TypeError, RuntimeError):  # pragma: no cover
                    pass


@_requires_qt
class TestTheModeHintIsTranslated:
    """v0.1.168 (A). Hasta aquí ``set_tool_mode`` emitía el texto de estado
    SIN ``tr()``, y los 34 hints tenían CERO entradas en español: activar
    este modo habría publicado una cadena inglesa nueva en pantalla."""

    def test_the_three_point_hint_has_spanish(self):
        from ogr_gui.i18n import _DICTS
        assert _HINT in _DICTS["es"]

    def test_entering_the_mode_emits_the_translated_hint(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import _DICTS, set_language
        with _canvas_ready() as (w, c):
            try:
                set_language("es")
                with _messages(c) as got:
                    c.set_tool_mode(ToolMode.ADD_SURFACE_3PT)
                assert got and got[-1] == _DICTS["es"][_HINT]
            finally:
                set_language("en")

    def test_the_hints_are_counted_and_capped(self):
        """Con ``==`` y no ``<=``, y los DOS números: la lección del 210,
        que dejó de medir nada mucho antes de que nadie lo notara. Fijar
        también el total impide satisfacer el techo borrando hints."""
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import _DICTS
        hints = [m.status_message for m in ToolMode if m.status_message]
        assert len(hints) == _HINTS_TOTAL
        sin = [h for h in hints if h not in _DICTS["es"]]
        assert len(sin) == _HINTS_WITHOUT_SPANISH

    def test_the_coverage_scanner_cannot_see_the_hints(self):
        """Y por eso el techo de arriba tiene que existir: ``set_tool_mode``
        llama a ``tr()`` con una VARIABLE, y el escáner AST de
        test_i18n_coverage_v141 sólo recoge literales constantes. Mismo
        agujero que v0.1.166 documentó para las etiquetas de acción."""
        from test_i18n_coverage_v141 import _wrapped_keys
        assert _HINT not in _wrapped_keys()
        # El del rechazo SÍ es literal, y por eso ése sí está cubierto.
        assert _REFUSAL in _wrapped_keys()


@_requires_qt
class TestWhatMustNotChange:

    def test_every_input_point_lies_on_the_returned_circle(self):
        """CONTROL, verde antes y después, y se dice: no prueba nada de
        D101. Sustituye a la instantánea «centro (2,2), radio 2√2» que
        proponía la ficha —que ya pasaba con 0.1.167 y por tanto no podía
        discriminar— por la identidad analítica que la generaliza."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.surface import SlipCircle
        trios = (((0, 0), (4, 0), (0, 4)),
                 ((0, 0), (2, 0), (1, 1)),
                 ((-3, 7), (11, -2), (5, 19)))
        for trio in trios:
            c = SlipCircle.from_three_points(*[Vertex(*p) for p in trio])
            for px, py in trio:
                d = math.hypot(px - c.centre_x, py - c.centre_y)
                assert d == pytest.approx(c.radius, abs=1e-12)

    def test_a_three_point_circle_survives_the_ogr_round_trip(self, tmp_path):
        """El contrato de 0.1.157 alcanza a un círculo nacido por ESTE
        camino: se escribe al archivo y vuelve."""
        from ogr_core.project import Project
        with _canvas_ready() as (w, c):
            w._actions[_KEY].trigger()
            for x, y in ((100, 100), (400, 120), (250, 400)):
                _press(c, x, y)
            hecho = w.project.user_surfaces[-1]
            out = tmp_path / "tres_puntos.ogr"
            w.project.save(out)
            back = Project.load(out)
            assert len(back.user_surfaces) == 1
            vuelto = back.user_surfaces[0]
            assert vuelto.centre_x == hecho.centre_x
            assert vuelto.centre_y == hecho.centre_y
            assert vuelto.radius == hecho.radius
            assert vuelto.id == hecho.id

    def test_the_message_budget_is_still_exactly_sixty_eight(self):
        """Rompe en las DOS direcciones: un ``showMessage`` nuevo con
        literal desnudo lo sube, y envolver uno de los que ya había lo
        baja. Los mensajes de esta versión van por ``tr()``, y ningún
        literal existente se ha tocado."""
        from test_i18n_coverage_v141 import (_UNWRAPPED_BUDGET,
                                             _UNWRAPPED_BUDGET_MESSAGES,
                                             _VISIBLE_MESSAGES,
                                             _unwrapped_count)
        assert _UNWRAPPED_BUDGET == 210
        assert _unwrapped_count(_VISIBLE_MESSAGES) == _UNWRAPPED_BUDGET_MESSAGES

    def test_every_wrapped_key_of_this_version_has_spanish(self):
        from ogr_gui.i18n import _DICTS
        for k in (_LABEL, _HINT, _REFUSAL):
            assert k in _DICTS["es"], k


class TestTheOtherModesNobodyEnters:
    """Regla 6: reportado y NO corregido.

    El censo que D101 hizo a ojo decía un modo huérfano. Medido por AST
    sobre toda llamada a ``set_tool_mode``/``_set_tool`` —y la única forma
    que no nombra un ToolMode literal es el propio reenviador
    ``_set_tool``, así que el censo es completo— son SEIS los que nadie
    activa, y esta versión sólo cablea uno.
    """

    def test_the_three_point_mode_is_wired_now(self):
        assert "ADD_SURFACE_3PT" in _activated_modes()

    def test_the_other_six_are_still_unreachable(self):
        """La evidencia del reporte. Se pondrá roja el día que alguien
        cablee uno, que es cuando la ficha del banco tiene que cambiar."""
        from ogr_gui.canvas.tool_mode import ToolMode
        todos = {m.name for m in ToolMode}
        assert todos - _activated_modes() == _NEVER_ENTERED

    def test_two_of_them_are_pure_scaffolding_like_this_one_was(self):
        """``MEASURE`` y ``ADD_SURFACE_CR`` tienen cursor y texto de estado
        y nadie los lee siquiera — el andamiaje exacto de D101.
        ``ADD_SURFACE_CR`` es además el modo del hermano que la ficha cita
        como el precedente que SÍ funciona: su acción va por diálogos y
        nunca entra en él."""
        from ogr_gui.canvas.tool_mode import ToolMode
        for name in ("MEASURE", "ADD_SURFACE_CR"):
            assert getattr(ToolMode, name).status_message
            assert name not in _activated_modes()
