# Vendored pydcs — provenance & license

This directory (`vendor/dcs/`) is a **vendored, UNMODIFIED copy of pydcs**, the
Digital Combat Simulator Python mission framework.

- Upstream: https://github.com/pydcs/dcs
- Source revision: **`412952c5ad5688783d8d53830280f316dbe311ff`**,
  2026-06-29 ([upstream commit](https://github.com/pydcs/dcs/commit/412952c5ad5688783d8d53830280f316dbe311ff)).
  Verified on 2026-10-02: all 108 upstream Python files match byte-for-byte,
  with no missing or additional Python modules. This is newer than the
  PyPI 0.15.0 release; the app imports this directory, not a pip installation.
- License: **GNU Lesser General Public License v3.0 (LGPL-3.0)** — full text in
  this directory as `COPYING.LESSER` (LGPL-3.0) and `COPYING` (GPL-3.0, which the
  LGPL incorporates by reference).
- Copyright: the pydcs authors / contributors.

## We do not modify pydcs source

DCS Mission Starter needs a few behavioural adjustments to pydcs (deterministic
onboard-number allocation, a frozen ambient-random default). **These are applied
at runtime by monkey-patching**, in `missiongen/_determinism.py` — the pydcs
source files here are left byte-for-byte as upstream. This keeps the vendored
library separable and replaceable, satisfying LGPL-3.0 §4/§5: a user may drop in
their own build of pydcs and the application will use it.

If you ever need to *change* pydcs itself, do it upstream (a PR to pydcs/dcs) or
in a clearly-marked patch — not by editing these files — so this copy stays a
clean mirror.
