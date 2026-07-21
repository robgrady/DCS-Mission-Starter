# Vendored pydcs — provenance & license

This directory (`vendor/dcs/`) is a **vendored, UNMODIFIED copy of pydcs**, the
Digital Combat Simulator Python mission framework.

- Upstream: https://github.com/pydcs/dcs
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
