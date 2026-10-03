"""Prove native seat assignment and Library promotion guards by breaking them."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TESTS = ['tests/test_veteran_wingmen.py', 'tests/test_refactor_browser.py']
CASES = [
    ('missiongen/player_seats.py', 'Skill.High if recipe.veteran_wingmen',
     'Skill.Good if recipe.veteran_wingmen', 'four_ship_has_one_player', 'veterans lose High skill'),
    ('missiongen/player_seats.py', 'unit.set_player()', 'unit.set_client()',
     'four_ship_has_one_player', 'solo flight loses its Player seat'),
    ('missiongen/player_seats.py', 'humans = recipe.slots - recipe.veteran_wingmen',
     'humans = recipe.slots', 'four_ship_has_one_player', 'all four aircraft become clients'),
    ('missiongen/recipe.py', '0 <= self.veteran_wingmen < self.slots',
     '0 <= self.veteran_wingmen <= self.slots', 'invalid_veteran_counts', 'all-AI recipe is accepted'),
    ('missiongen/phases/mission_briefing.py', 'flight_line += " " + stats["flight_composition"]',
     'flight_line += ""', 'four_ship_has_one_player', 'native brief loses the AI composition'),
    ('missiongen/brief.py', 'execution += " " + stats["flight_composition"]',
     'execution += ""', 'pdf_execution_describes', 'PDF execution text loses the AI composition'),
    ('missiongen/brief.py', 'L += ["**Your flight:** " + stats["flight_composition"], ""]',
     'L += []', 'veterans_are_explained', 'Markdown brief loses the AI composition'),
    ('frontend/index.html', '<section id="library">',
     '<section id="library"><p>New in DCS</p>', 'library_has_no_static_new_module', 'static promotion returns'),
]


def run(selector):
    result = subprocess.run([sys.executable, '-m', 'pytest', *TESTS, '-q', '-x', '-k', selector],
                            cwd=ROOT, capture_output=True, text=True)
    return result


def main():
    baseline = run('veteran or veterans or four_ship or fixed_procedural or formation_keeps or old_four_ship or share_links_keep or pdf_execution_describes')
    if baseline.returncode:
        raise SystemExit('Baseline failed:\n' + baseline.stdout + baseline.stderr)
    originals = {path: (ROOT/path).read_text() for path, *_ in CASES}
    try:
        for path, anchor, replacement, selector, label in CASES:
            original = originals[path]
            # Some anchors occur in both summary and assignment; change the assignment only.
            if label == 'all four aircraft become clients':
                anchor = 'def assign_seats(group, recipe):\n    ' + anchor
                replacement = 'def assign_seats(group, recipe):\n    ' + replacement
            assert original.count(anchor) == 1, (path, anchor)
            (ROOT/path).write_text(original.replace(anchor, replacement))
            try:
                result = run(selector)
                if result.returncode != 1:
                    raise SystemExit(f'WEAK or invalid run: {label}\n{result.stdout}\n{result.stderr}')
                print('caught:', label, flush=True)
            finally:
                (ROOT/path).write_text(original)
    finally:
        for path, original in originals.items():
            (ROOT/path).write_text(original)
    print(f'{len(CASES)} caught; 0 weak; baseline restored.')


if __name__ == '__main__':
    main()
