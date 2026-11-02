# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where the slices of a search's population wait on disk (v0.1.408, D383).

Every evaluation of a search kept its ``Slices`` in memory: 57 kB per
surface, 90 % of it slices, so the 124 848 evaluations of the interface test
of 0.1.397 held 7.1 GB in one result, and the window keeps two while it
recomputes (D362). Only the critical surface and the ones the user picks are
ever read slice by slice; the rest is read surface by surface (Interpret,
``results_query``) or once over in order (the ``.h5``, the back analysis).

So a run that asks for it (``run_analysis``, the back analysis) gives its
grid search a :class:`SliceStore`, and every evaluation the grid keeps hands
its slices to the store as it is appended: one record per evaluation in one
append-only file of a private folder, and a :class:`SpilledSlices` in its
place that knows its length, the base of the surface and its area without
reading the file. The critical surface comes back to memory at the end of
the run. The design and its measurements are the owner's review of
2026-11-01 (``_auditoria/P8_interfaz/D383_revision_diseno.md`` in the
verification bench): 6.8 kB per evaluation instead of 57.4 (tracemalloc),
about 120 us per evaluation to write, 0.18 ms to read one surface back.

Decided there, and why:

* records are pickled with a ``dispatch_table`` entry for ``Material``, which
  puts the material's position in the store's table in the record instead
  of the material. ``persistent_id`` does the same but is called for every
  object of the record, floats included: 327 against 101 us per record.
  The slices read back share the run's materials, and ``detach_materials``
  rebinds the table without reading a record;
* compressed with zlib at level 1 (the owner's decision): 8.0 to 3.1 kB per
  record for 44 us more to write and 16 us more to read;
* only a population of :data:`SPILL_MIN_CIRCLES` nominal circles or more is
  spilled: below that a run pays nothing and makes no folder;
* folders a dead session left behind are removed when a store is made, if
  they are more than :data:`ORPHAN_AGE_S` old and removing them works: the
  open file of a live session forbids it on Windows, and on Linux its open
  descriptor goes on reading.

v0.1.409 (D383, V2) — a grid split across a process pool spills too. The
search reaches each worker with a :class:`_BatchStore`, the same store kept
in that worker's memory for its batch: every evaluation is pickled and
compressed there, and the batch comes back as records (:class:`_Pending`)
and the batch's table of materials, not as objects. The parent writes the
records to its file as each batch arrives (:meth:`SliceStore.adopt_part`),
and the batch's table goes on the end of its own: a record keeps the
positions of its batch's table, so its slices know where that table starts
(``_base``). The parent no longer unpickles every slice of the grid.

v0.1.410 (D383, V3) — every search spills, not only the grid: each says how
many surfaces it plans (``nominal_surfaces``) and keeps every evaluation
through one door (``BaseSearch._keep``). A rapid drawdown's ``screen_states``
are spilled with their result, sharing its record where they share its
slices. A result that crosses a process inside :func:`arriving` (the API
reading an agent's job) is spilled again into a store of the process that
reads it, instead of bringing every slice back into memory (the owner's
decision of the review). The walk a search steered (``steered``) stays on
disk: only its identity is ever asked for.
"""
from __future__ import annotations

import array
import collections
import contextlib
import copyreg
import io
import os
import pickle
import shutil
import tempfile
import threading
import time
import weakref
import zlib

#: The owner's decision (2026-11-01): a grid of fewer nominal circles keeps
#: its slices in memory, as every run did before v0.1.408. Tests set it to 0.
#: v0.1.410 (V3): every search, by the surfaces it plans (``nominal_surfaces``).
SPILL_MIN_CIRCLES = 2000

#: How old a folder of another session has to be before a new store removes
#: it, in seconds.
ORPHAN_AGE_S = 3600.0

#: The folder under the temporary directory that holds one folder per store.
#: Its own, because the temporary directory itself held 41 787 entries on the
#: development machine: looking through it took 2.4 s cold.
FOLDER = "ogr_slices"

#: Slices read back and kept, the latest first: whoever reads one surface
#: indexes it several times (``slices[0]``, then the loop).
_RECENT = 16

#: zlib level of a record (the owner's decision).
_LEVEL = 1

# The scalars of ``Slices`` besides the list; a SpilledSlices keeps them.
_SCALARS = ("tension_crack_force", "tension_crack_arm", "tension_crack_wall",
            "design_sense", "load_factors")

_LOADING = threading.local()

#: The store that records arriving from another process go to, inside
#: :func:`arriving` on this thread.
_ARRIVING = threading.local()


def _material_at(i):
    """A material of a record, by its position in the table of the store
    being read (set by :func:`_unpickle` on this thread), counted from where
    the record's batch starts in it."""
    return _LOADING.table[_LOADING.base + i]


def _unpickle(data: bytes, table: list, base: int = 0) -> list:
    _LOADING.table = table
    _LOADING.base = base
    try:
        return pickle.loads(zlib.decompress(data))
    finally:
        _LOADING.table = None


def _from_record(data: bytes, table: list, count: int, scalars: dict,
                 base: int = 0, xs=None, ys=None, area=None):
    """What a pickled :class:`SpilledSlices` becomes when it is read back:
    inside :func:`arriving`, a :class:`SpilledSlices` of this process's
    store (v0.1.410); elsewhere, a ``Slices`` read from the record."""
    arrivals = getattr(_ARRIVING, "arrivals", None)
    if arrivals is not None and xs is not None:
        return arrivals.respill(data, table, count, scalars, base, xs, ys,
                                area)
    from .slicer import Slices
    return Slices(slices=_unpickle(data, table, base), **scalars)


class _Arrivals:
    """The records of one :func:`arriving` block: one store, made on the
    first, and where each sender's table starts in its table."""

    def __init__(self) -> None:
        self.store = None
        self._bases: dict = {}
        self._tables: list = []    # alive, so their ids stay theirs

    def respill(self, data, table, count, scalars, base, xs, ys, area):
        if self.store is None:
            self.store = SliceStore()
        store = self.store
        start = self._bases.get(id(table))
        if start is None:
            with store._lock:
                start = self._bases[id(table)] = len(store.table)
                store.table.extend(table)
                for i, m in enumerate(table):
                    store._position.setdefault(id(m), start + i)
            self._tables.append(table)
        stub = SpilledSlices()
        stub._store = store
        stub._off, stub._n = store._write(data)
        stub._base = start + base
        stub._count, stub._xs, stub._ys, stub.area = count, xs, ys, area
        for k, v in scalars.items():
            setattr(stub, k, v)
        return stub


@contextlib.contextmanager
def arriving():
    """Unpickle results inside this block to keep their spilled slices on
    disk: each record that arrives is written to one new store of this
    process (made only if one arrives) instead of being read back into
    memory. Used where a result crosses a process and stays: the API
    reading the file an agent's job wrote (v0.1.410, the owner's decision
    "volver a volcar")."""
    previous = getattr(_ARRIVING, "arrivals", None)
    _ARRIVING.arrivals = _Arrivals()
    try:
        yield
    finally:
        _ARRIVING.arrivals = previous


def _close_and_remove(fh, path: str) -> None:
    try:
        fh.close()
    finally:
        shutil.rmtree(path, ignore_errors=True)


def remove_folders_of(pid: int) -> int:
    """Remove the store folders of process ``pid``, which has ended; how
    many went. A process that is killed (an agent's job cancelled: its whole
    tree is) never runs its finalizers, and its folder would wait for
    :func:`remove_orphans`. A folder whose file a live process holds open,
    as a later process given the same number would, cannot be removed on
    Windows and is left as it is."""
    root = os.path.join(tempfile.gettempdir(), FOLDER)
    prefix = "%d_" % pid
    gone = 0
    try:
        entries = list(os.scandir(root))
    except OSError:
        return 0
    for e in entries:
        if e.name.startswith(prefix) and e.is_dir():
            shutil.rmtree(e.path, ignore_errors=True)
            gone += not os.path.exists(e.path)
    return gone


def remove_orphans(root: str, age_s: float = ORPHAN_AGE_S,
                   keep: str = "") -> int:
    """Remove the store folders under ``root`` older than ``age_s``, except
    ``keep``; how many went. A folder whose file a live session holds open
    cannot be removed on Windows and is left as it is."""
    gone = 0
    now = time.time()
    try:
        entries = list(os.scandir(root))
    except OSError:
        return 0
    for e in entries:
        if e.path == keep:
            continue
        try:
            if not e.is_dir() or now - e.stat().st_mtime < age_s:
                continue
        except OSError:
            continue
        shutil.rmtree(e.path, ignore_errors=True)
        gone += not os.path.exists(e.path)
    return gone


class SliceStore:
    """The slices of one run's population, on disk.

    One folder and one append-only file, open while the store lives; one
    table of the materials the records name. Thread safe: the window and the
    thread that writes the ``.h5`` read it at the same time.
    """

    def __init__(self) -> None:
        root = os.path.join(tempfile.gettempdir(), FOLDER)
        os.makedirs(root, exist_ok=True)
        self.path = tempfile.mkdtemp(prefix="%d_" % os.getpid(), dir=root)
        remove_orphans(root, keep=self.path)
        self._fh = open(os.path.join(self.path, "slices.bin"), "w+b")
        self._lock = threading.Lock()
        self._end = 0
        # A seek empties the write buffer and makes every record a system
        # call (63 against 9 us): the file is moved only after a read.
        self._at_end = True
        self.table: list = []
        self._position: dict = {}
        self._dispatch = None
        self._recent: collections.OrderedDict = collections.OrderedDict()
        self.records = 0
        self.loads = 0
        self._finalizer = weakref.finalize(self, _close_and_remove,
                                           self._fh, self.path)

    def __reduce__(self):
        # v0.1.409 (V2) — pickled (a search shipped to a pool's worker) as
        # a store in that worker's memory: the file belongs to this process,
        # and the batch's records come back to it (``adopt_part``)
        return (_BatchStore, ())

    # ------------------------------------------------------------------
    def _material_reduce(self, m):
        i = self._position.get(id(m))
        if i is None:
            i = self._position[id(m)] = len(self.table)
            self.table.append(m)
        return _material_at, (i,)

    def _dumps(self, slice_list: list) -> bytes:
        if self._dispatch is None:
            from ogr_core.materials import Material
            self._dispatch = copyreg.dispatch_table.copy()
            self._dispatch[Material] = self._material_reduce
        buf = io.BytesIO()
        p = pickle.Pickler(buf, protocol=pickle.HIGHEST_PROTOCOL)
        p.dispatch_table = self._dispatch
        p.dump(slice_list)
        return zlib.compress(buf.getvalue(), _LEVEL)

    def _write(self, data: bytes) -> tuple:
        with self._lock:
            if not self._at_end:
                self._fh.seek(self._end)
                self._at_end = True
            self._fh.write(data)
            off = self._end
            self._end += len(data)
        self.records += 1
        return off, len(data)

    def _read(self, off: int, n: int) -> bytes:
        with self._lock:
            self._at_end = False
            self._fh.seek(off)
            return self._fh.read(n)

    def load(self, off: int, n: int, base: int = 0) -> list:
        """The slice list of one record, read from the file."""
        lst = _unpickle(self._read(off, n), self.table, base)
        self.loads += 1
        return lst

    def recent(self, off: int, n: int, base: int = 0) -> list:
        """The slice list of one record, from the latest read when it is
        one of them."""
        with self._lock:
            lst = self._recent.get(off)
            if lst is not None:
                self._recent.move_to_end(off)
                return lst
        lst = self.load(off, n, base)
        with self._lock:
            self._recent[off] = lst
            while len(self._recent) > _RECENT:
                self._recent.popitem(last=False)
        return lst

    # ------------------------------------------------------------------
    def spill(self, res) -> None:
        """Put the slices of ``res`` (an LEMResult) in the store and a
        :class:`SpilledSlices` in their place. Nothing to do for a result
        without slices, or whose slices are already spilled."""
        sl = getattr(res, "slices", None)
        if sl is None or type(sl) is SpilledSlices or not len(sl):
            return
        from .interpretation import surface_area
        stub = SpilledSlices()
        stub._store = self
        stub._off, stub._n = self._write(self._dumps(sl.slices))
        stub._base = 0
        stub._count = len(sl)
        # the base, as ``surface_path`` reads it: the left end of the first
        # slice, then the right end of every slice
        xs = array.array("d", [sl[0].base_x_left])
        ys = array.array("d", [sl[0].base_y_left])
        for s in sl:
            xs.append(s.base_x_right)
            ys.append(s.base_y_right)
        stub._xs, stub._ys = xs, ys
        # the same function on the same slices: the same float
        stub.area = surface_area(res)
        for k in _SCALARS:
            setattr(stub, k, getattr(sl, k))
        res.slices = stub
        # v0.1.410 (V3) — a rapid drawdown's screen states, each a result of
        # its own: the one whose slices the result publishes shares its
        # record, the other gets one
        for state in getattr(res, "screen_states", None) or ():
            if state is res:
                continue
            if getattr(state, "slices", None) is sl:
                state.slices = stub
            else:
                self.spill(state)

    def detach(self, live: dict, copy_of) -> None:
        """``detach_materials`` for the records: the project's own
        materials in the table become ``copy_of(material)``, which the
        slices still in memory share."""
        with self._lock:
            for i, m in enumerate(self.table):
                if id(m) in live:
                    self.table[i] = copy_of(m)
            self._position = {id(m): i for i, m in enumerate(self.table)}
            self._recent.clear()

    def adopt_part(self, part) -> None:
        """The records of a pool's batch into this store (v0.1.409, V2):
        ``part`` is the batch's ``SearchResult`` as it arrived, its
        evaluations holding :class:`_Pending` records and ``_worker_table``
        the batch's materials. A batch from a worker without a store has
        neither and is left as it is."""
        table = getattr(part, "_worker_table", None)
        if table is None:
            return
        with self._lock:
            base = len(self.table)
            self.table.extend(table)
            for i, m in enumerate(table):
                self._position.setdefault(id(m), base + i)
        part._worker_table = None
        made: dict = {}

        def adopt(p):
            # one record per _Pending: a screen state that shared its
            # result's slices arrives sharing the same _Pending (V3)
            stub = made.get(id(p))
            if stub is None:
                stub = made[id(p)] = SpilledSlices()
                stub._store = self
                stub._off, stub._n = self._write(p.data)
                stub._base = base
                stub._count, stub._xs, stub._ys, stub.area = (p.count, p.xs,
                                                              p.ys, p.area)
                for k, v in zip(_SCALARS, p.scalars):
                    setattr(stub, k, v)
            return stub
        for res in part.evaluations:
            if type(res.slices) is _Pending:
                res.slices = adopt(res.slices)
            for state in getattr(res, "screen_states", None) or ():
                if type(getattr(state, "slices", None)) is _Pending:
                    state.slices = adopt(state.slices)

    def _reduce_stub(self, stub):
        # the record as it is on disk and the store's table, never the
        # objects: a pickler keeps every object it wrote until the end, so
        # a result pickled whole (the API's result.pkl) would hold every
        # evaluation's slices in memory again
        # v0.1.410 (V3) — with the base and the area, so a process that
        # reads it ``arriving`` keeps it spilled
        return (_from_record,
                (self._read(stub._off, stub._n), self.table, stub._count,
                 {k: getattr(stub, k) for k in _SCALARS}, stub._base,
                 stub._xs, stub._ys, stub.area))


class _BatchStore(SliceStore):
    """A :class:`SliceStore` kept in a pool worker's memory for one batch
    (v0.1.409, V2): what a store shipped with the search becomes there.
    Its records go back to the parent as records (:class:`_Pending`), with
    the batch's table of materials."""

    def __init__(self) -> None:
        self.path = None
        self._chunks: list = []
        self._lock = threading.Lock()
        self.table = []
        self._position = {}
        self._dispatch = None
        self._recent = collections.OrderedDict()
        self.records = 0
        self.loads = 0

    def __reduce__(self):
        return (type(None), ())

    def _write(self, data: bytes) -> tuple:
        self._chunks.append(data)
        self.records += 1
        return len(self._chunks) - 1, len(data)

    def _read(self, off: int, n: int) -> bytes:
        return self._chunks[off]

    def _reduce_stub(self, stub):
        return (_Pending, (self._chunks[stub._off], stub._count, stub._xs,
                           stub._ys, stub.area,
                           tuple(getattr(stub, k) for k in _SCALARS)))


class _Pending:
    """One record of a pool's batch on its way to the parent's store: the
    bytes and what a :class:`SpilledSlices` keeps in memory. Never read:
    :meth:`SliceStore.adopt_part` replaces it as the batch arrives."""

    __slots__ = ("data", "count", "xs", "ys", "area", "scalars")

    def __init__(self, data, count, xs, ys, area, scalars):
        self.data, self.count, self.xs, self.ys = data, count, xs, ys
        self.area, self.scalars = area, scalars

    def __len__(self) -> int:
        return self.count


class SpilledSlices:
    """In place of the ``Slices`` of one evaluation whose records are in a
    :class:`SliceStore`.

    Its length, the base of the surface (:meth:`trace`), the area of the
    mass and the scalars of ``Slices`` are here; anything else reads the
    record. Two reads of the same surface give the same objects while it is
    one of the store's latest, and different but equal ones after.
    """

    __slots__ = ("_store", "_off", "_n", "_base", "_count", "_xs", "_ys",
                 "area") + _SCALARS

    def __len__(self) -> int:
        return self._count

    def trace(self) -> list:
        """``[(x, y), ...]``: the base, as ``surface_path`` gives it."""
        return list(zip(self._xs, self._ys))

    @property
    def store(self) -> SliceStore:
        return self._store

    @property
    def slices(self) -> list:
        return self._store.recent(self._off, self._n, self._base)

    def __iter__(self):
        return iter(self.slices)

    def __getitem__(self, i):
        return self.slices[i]

    def total_weight(self) -> float:
        return sum(s.weight for s in self.slices)

    def to_list(self) -> list:
        return [s.to_dict() for s in self.slices]

    def materialize(self):
        """A ``Slices`` of its own, read from the file."""
        from .slicer import Slices
        return Slices(slices=self._store.load(self._off, self._n, self._base),
                      **{k: getattr(self, k) for k in _SCALARS})

    def __eq__(self, other):
        if isinstance(other, SpilledSlices):
            other = other.materialize()
        return self.materialize() == other

    __hash__ = None

    def __reduce__(self):
        # what crosses is the record, never the objects: the store says how
        # (a pool worker's batch sends it on to the parent's store)
        return self._store._reduce_stub(self)

    def __repr__(self) -> str:
        return "SpilledSlices(%d slices at %d)" % (self._count, self._off)


def wants_store(search) -> bool:
    """Whether ``search`` keeps a population worth spilling: one that plans
    :data:`SPILL_MIN_CIRCLES` surfaces or more (a grid's nominal circles;
    since v0.1.410 every search's ``nominal_surfaces``). The one rule
    ``run_analysis`` and the back analysis ask."""
    nominal = getattr(search, "nominal_surfaces", None)
    planned = nominal() if nominal is not None else None
    return planned is not None and planned >= SPILL_MIN_CIRCLES


def rehydrate(res) -> None:
    """Give ``res`` its slices back in memory, if they were spilled, and its
    screen states theirs (the one that shared them shares them again)."""
    sl = getattr(res, "slices", None)
    back = None
    if type(sl) is SpilledSlices:
        back = res.slices = sl.materialize()
    for state in getattr(res, "screen_states", None) or ():
        if state is res:
            continue
        if back is not None and getattr(state, "slices", None) is sl:
            state.slices = back
        else:
            rehydrate(state)


def rehydrate_special(result) -> None:
    """The surfaces a search result names, back in memory: the critical,
    the minima, the optimised one and the user's. Their slices are read
    whole by the notes of the run, the window and the report.

    v0.1.410 (V3) — not the steered ones: a Slope Search's walk puts
    hundreds there, and only their identity is asked for (the statistics
    leave them out); the optimised surfaces among them are here anyway."""
    for r in (result.critical, result.optimized, *result.minima,
              *result.user_evaluations):
        if r is not None:
            rehydrate(r)


__all__ = ["SPILL_MIN_CIRCLES", "SliceStore", "SpilledSlices", "arriving",
           "rehydrate",
           "rehydrate_special", "remove_folders_of", "remove_orphans",
           "wants_store"]
