"""Validate the deliberately written documentation decision for each release."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / 'docs/manual-release-review.json'

def errors(version, root=ROOT):
    path = root / 'docs/manual-release-review.json'
    try:
        review = json.loads(path.read_text())
    except (OSError, ValueError):
        return ['missing or invalid docs/manual-release-review.json']
    findings = []
    if review.get('version') != version:
        findings.append('manual review belongs to a different release')
    required = review.get('documentation_required')
    if not isinstance(required, bool):
        findings.append('documentation_required must be explicitly true or false')
    if not review.get('reason') or not review.get('sections_reviewed'):
        findings.append('record the documentation impact and sections reviewed')
    source = root / 'docs/USER_GUIDE.md'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if review.get('source_sha256') != digest:
        findings.append('manual changed after review; review it again')
    previous = review.get('previous_source_sha256')
    if not previous or (required is True and previous == digest):
        findings.append('documentation is required but the manual was not updated')
    if required is False and previous != digest:
        findings.append('manual changed; record that documentation was updated')
    return findings

if __name__ == '__main__':
    import sys
    from missiongen import __version__
    problems = errors(__version__)
    if problems:
        raise SystemExit('\n'.join(problems))
    print('User Manual review recorded for ' + __version__)
