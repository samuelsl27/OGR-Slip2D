# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
How big a dialog opens, and the pieces that keep its text whole.

v0.1.315 (D293). Two dialogs opened at a size written for English and
cut their Spanish buttons and notes: the transient one at 520 px when its
row of buttons needed 1156, the hydraulic one with its parameters squeezed
into a 190 px column that scrolled sideways.

v0.1.326 (D319–D321). A census of what else a dialog shows found two more
ways to cut it:

* a word-wrapped label asks for more height the narrower it is, and Qt does
  not raise a WINDOW's minimum height for it: the layout's minimum is taken
  with the text on as few lines as possible. Scale Boundary opened with its
  boxes 13 px tall of 25, Add Grid with them at 21, and seven more squashed
  theirs when shrunk. ``hold_wrapped_height`` keeps the minimum height at
  what the layout needs at the window's minimum width;
* a check box keeps its text on one line, so a long one set the minimum
  width of its whole dialog (740 px for the anchors option of Design
  Standard in Spanish). ``WrappingCheckBox`` wraps it like a label.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QScrollArea,
                               QSizePolicy, QStyle, QStyleOptionButton,
                               QStylePainter, QWidget)


def open_at_content_size(dialog: QWidget, at_least: QSize) -> None:
    """Resize ``dialog`` to what its content asks for, never below
    ``at_least`` and never beyond the screen it opens on.

    The layout still keeps it from shrinking under its minimum, and
    :func:`hold_wrapped_height` keeps that minimum tall enough for its
    wrapped text, so this only decides where it starts.
    """
    hold_wrapped_height(dialog)
    size = dialog.sizeHint().expandedTo(at_least)
    layout = dialog.layout()
    if layout is not None and layout.hasHeightForWidth():
        size.setHeight(max(size.height(),
                           layout.totalHeightForWidth(size.width())))
    screen = dialog.screen()
    if screen is not None:
        size = size.boundedTo(screen.availableGeometry().size())
    dialog.resize(size)


class _WrappedHeight(QObject):
    """The filter behind :func:`hold_wrapped_height`.

    It runs when the window is shown and every time its layout is asked to
    lay out again. By then the layout has set the window's minimum, so the
    content can change (a page swapped, a row shown) and the hold follows
    it. A minimum set once would have the flaw of D321: an explicit minimum
    replaces the one the layout keeps up to date.

    It reaches its window as its Qt parent and keeps no Python reference
    to it, and the window finds it by name: a Python cycle between the two
    would leave them to the garbage collector, which clears one side's
    attributes while the Qt objects still live (and, from a thread of a
    process pool, destroys Qt objects: D310).
    """

    NAME = "ogr_wrapped_height"

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName(self.NAME)
        window.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() in (QEvent.LayoutRequest, QEvent.Show) \
                and obj is self.parent():
            self.hold()
        return False

    def hold(self) -> None:
        window = self.parent()
        if window is None:
            return
        layout = window.layout()
        if layout is None:
            return
        layout.activate()
        need = layout.totalMinimumSize().height()
        if layout.hasHeightForWidth():
            # the narrowest the window can be is where wrapped text takes
            # the most lines, so this height serves every wider one too
            need = max(need, layout.totalHeightForWidth(window.minimumWidth()))
        if need != window.minimumHeight():
            window.setMinimumHeight(need)


def hold_wrapped_height(window: QWidget) -> None:
    """Keep ``window``'s minimum height at what its layout needs at the
    window's minimum width, where its wrapped text is tallest.

    Without it a window short of height squeezes its fixed-height boxes
    instead (their size policy does not stop a layout that has no room).
    Installing it twice does nothing more.
    """
    hold = window.findChild(_WrappedHeight, _WrappedHeight.NAME,
                            Qt.FindDirectChildrenOnly)
    if hold is None:
        hold = _WrappedHeight(window)
    hold.hold()


def list_width(view: QAbstractItemView) -> int:
    """The width ``view`` needs to show its widest item whole: the items,
    the frame on both sides and, unless it is switched off, the vertical
    scroll bar a longer list will show."""
    width = max(view.sizeHintForColumn(0), 0) + 2 * view.frameWidth()
    if view.verticalScrollBarPolicy() != Qt.ScrollBarAlwaysOff:
        width += view.verticalScrollBar().sizeHint().width()
    return width


class WrappingCheckBox(QCheckBox):
    """A check box whose text wraps to the width it is given.

    It asks for the height its text needs at the width the layout gives it,
    as a word-wrapped ``QLabel`` does. Everything else is a check box's own:
    ``text()``, the state, the tooltip, and a click anywhere on the text.
    """

    #: The narrowest its text column gets, in average characters. A
    #: word-wrapped QLabel has no floor and can be squeezed to a word per
    #: line; thirty characters keeps a short clause together.
    MIN_CHARS = 30
    #: The widest it asks for, in average characters: QLabel's own limit
    #: for word-wrapped text, so a wrapped check box and a wrapped note
    #: next to it ask for the same column.
    PREFERRED_CHARS = 80

    _FLAGS = (Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap
              | Qt.TextShowMnemonic)

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        policy = self.sizePolicy()
        # a check box's own policies would undo the wrapping: Minimum across
        # makes its size hint the least it can be given, one line or not,
        # and Fixed down caps it at that one line's height (a layout never
        # gives a Fixed item more than its hint). A word-wrapped QLabel is
        # Preferred both ways.
        policy.setHorizontalPolicy(QSizePolicy.Preferred)
        policy.setVerticalPolicy(QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    # ---- geometry ------------------------------------------------------
    def _option(self) -> QStyleOptionButton:
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        return opt

    def _text_left(self) -> int:
        """Where the style starts the text: past the box and its gap."""
        opt = self._option()
        opt.rect = QRect(0, 0, max(self.width(), 1), self._line_height())
        return self.style().subElementRect(
            QStyle.SE_CheckBoxContents, opt, self).left()

    def _line_height(self) -> int:
        return super().sizeHint().height()

    def _text_height(self, width: int) -> int:
        box = QRect(0, 0, max(width, 1), 1 << 20)
        return self.fontMetrics().boundingRect(
            box, self._FLAGS, self.text()).height()

    def _top(self) -> int:
        """The first line sits where a one-line check box puts its text."""
        return max((self._line_height() - self.fontMetrics().height()) // 2,
                   0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        text = self._text_height(width - self._text_left())
        return max(self._line_height(), text + 2 * self._top())

    def sizeHint(self) -> QSize:  # noqa: N802
        one = super().sizeHint()
        cap = (self._text_left()
               + self.fontMetrics().averageCharWidth() * self.PREFERRED_CHARS)
        width = min(one.width(), cap)
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        one = super().minimumSizeHint()
        narrow = (self._text_left()
                  + self.fontMetrics().averageCharWidth() * self.MIN_CHARS)
        return QSize(min(one.width(), narrow), one.height())

    # ---- drawing and clicking -------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QStylePainter(self)
        opt = self._option()
        text, opt.text = opt.text, ""
        # the box beside the first line, not centred on the whole text
        opt.rect = QRect(0, 0, self.width(), self._line_height())
        painter.drawControl(QStyle.CE_CheckBox, opt)
        left = self._text_left()
        rect = QRect(left, self._top(), self.width() - left,
                     self.height() - self._top())
        self.style().drawItemText(painter, rect, self._FLAGS, self.palette(),
                                  self.isEnabled(), text,
                                  QPalette.WindowText)

    def hitButton(self, pos) -> bool:  # noqa: N802
        return self.rect().contains(pos)


class VerticalScrollArea(QScrollArea):
    """A scroll area as wide as its content: it scrolls up and down only.

    ``QScrollArea`` asks for almost no width, so a layout short of room
    gives it a sliver and its content scrolls sideways. This one asks for
    the width of the widget it holds plus the vertical bar, so its column
    is never narrower than the labels and buttons inside.
    """

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        inner = self.widget()
        if inner is None:
            return hint
        frame = 2 * self.frameWidth()
        bar = self.verticalScrollBar().sizeHint().width()
        return QSize(inner.minimumSizeHint().width() + bar + frame,
                     hint.height())
