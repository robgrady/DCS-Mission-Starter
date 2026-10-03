# Project rules

Read `docs/AGENT_HANDBOOK.md` before changing mission generation.

## Version every change

Owner instruction, 3 October 2026: every delivered change must increment the
application version using semantic versioning. Development and architecture
branches are included; do not retain a production version stamp on changed code.

- PATCH: fixes, data corrections, documentation corrections and compatible
  internal refactoring.
- MINOR: new backwards-compatible user capabilities.
- MAJOR: breaking public API, recipe/share-link or content contracts.

Each change batch must update `missiongen/__init__.py`, add its CHANGELOG entry
and update current version references. Separate delivered change batches get
separate versions. Never reuse a released version for different source/artifacts
or deploy changes under an older version. A future architecture milestone does
not postpone intermediate version bumps and does not by itself justify a major
version. Use explicit prerelease versions only if the release tooling supports
them; the current tooling uses X.Y.Z.

Run `scripts/release.sh X.Y.Z` for release artifacts and checks. Increment pack
content versions when generated mission content changes. Commit and push the
exact validated release, tag it, deploy it when authorized, and verify the
running version on every Fly machine. Keep source frozen while release checks
run. Save deployment evidence outside the versioned source tree.
