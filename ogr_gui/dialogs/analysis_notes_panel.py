# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Everything the last analysis had to say, not just its first sentence.

``run_analysis`` returns a list of notes and the window kept it in
``last_compute_warnings`` — then showed ``[0]`` in the status bar for
fifteen seconds and dropped the rest on the floor. The command-line
interface has printed all of them since v0.1.77, so the two front ends
disagreed about what the same run said, and the graphical one was the
lossy side.

That mattered more with every note added. The run can now say that the
reported surface leans on a near-zero m-alpha, that its centre sat on the
edge of the search grid, that a bolt is drawn head-first into the stable
ground, that a weak-layer case set had to be truncated, that a method was
ticked but is not registered, and — since v0.1.155 — how many of the
placed supports put no force on the surface it reports. Any one of those
could be the sentence that mattered, and which one survived was decided
by the order they happen to be appended in.

Non-modal on purpose: the notes are read WHILE the model is being looked
at, and a modal dialog blocks forever without a display, which is what
the test suite runs in.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ogr_gui.i18n import tr

#: Notes arrive as ``"<method id>: <sentence>"`` when they are about one
#: method's reported surface, and bare when they are about the model —
#: ``settings_warnings`` writes those before any method runs. Splitting on
#: the first colon would cut sentences that contain one, so the prefix is
#: only taken when it looks like an identifier: no spaces, and known to
#: the registry when the registry can be reached.
_MODEL_GROUP = "Model"


def _split(note: str) -> tuple:
    """``(group, sentence)`` for one note line."""
    head, sep, tail = note.partition(": ")
    if sep and head and " " not in head:
        return head, tail
    return _MODEL_GROUP, note


class AnalysisNotesPanel(QDialog):
    """Non-modal list of the notes from the last analysis."""

    def __init__(self, notes=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Analysis Notes"))
        self.setModal(False)
        self.resize(760, 420)

        v = QVBoxLayout(self)

        self.lbl_head = QLabel("")
        self.lbl_head.setWordWrap(True)
        v.addWidget(self.lbl_head)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Note")])
        self.tree.setColumnWidth(0, 700)
        self.tree.setWordWrap(True)
        v.addWidget(self.tree, 1)

        row = QHBoxLayout()
        self.btn_copy = QPushButton(tr("Copy all"))
        self.btn_copy.clicked.connect(self._copy_all)
        row.addWidget(self.btn_copy)
        row.addStretch(1)
        v.addLayout(row)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.close)
        v.addWidget(bb)

        self.populate(notes)

    # ==================================================================
    def populate(self, notes=()) -> None:
        """Fill the tree from a list of note lines.

        Re-callable, so the same panel refreshes after a recompute
        instead of a second window opening on top of the first.
        """
        self.notes = [str(n) for n in (notes or [])]
        self.tree.clear()
        if not self.notes:
            self.lbl_head.setText(tr(
                "The last analysis produced no notes."))
            self.btn_copy.setEnabled(False)
            return

        self.btn_copy.setEnabled(True)
        self.lbl_head.setText(tr(
            "%d note(s) from the last analysis. They report what the run "
            "decided or could not do; none of them changes a factor of "
            "safety.") % len(self.notes))

        groups: dict = {}
        for note in self.notes:
            group, sentence = _split(note)
            groups.setdefault(group, []).append(sentence)

        # The model-wide notes first: they are about the problem as posed,
        # so they are read before anything about one method's answer.
        for group in sorted(groups, key=lambda g: (g != _MODEL_GROUP, g)):
            sentences = groups[group]
            label = tr("Model") if group == _MODEL_GROUP else group
            top = QTreeWidgetItem(["%s (%d)" % (label, len(sentences))])
            for sentence in sentences:
                top.addChild(QTreeWidgetItem([sentence]))
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)

    # ==================================================================
    def _copy_all(self) -> None:
        """Put every note on the clipboard, one per line.

        The notes are what gets pasted into a report or an email, and
        retyping a paragraph off a screen is how a warning stops being
        quoted at all.
        """
        from PySide6.QtWidgets import QApplication

        clip = QApplication.clipboard()
        if clip is not None:
            clip.setText("\n".join(self.notes))
