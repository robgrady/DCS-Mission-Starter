"""Assign human seats and veteran AI inside the player's own flight."""
from dcs.unit import Skill


def assign_seats(group, recipe):
    humans = recipe.slots - recipe.veteran_wingmen
    for index, unit in enumerate(group.units):
        if index < humans:
            if humans == 1:
                unit.set_player()
            else:
                unit.set_client()
        else:
            # Preserve authored two-ship wingmen when no custom AI was requested.
            unit.skill = Skill.High if recipe.veteran_wingmen else Skill.Excellent


def flight_summary(recipe):
    humans = recipe.slots - recipe.veteran_wingmen
    human_label = "1 player aircraft" if humans == 1 else f"{humans} multiplayer client aircraft"
    ai_label = "wingman" if recipe.veteran_wingmen == 1 else "wingmen"
    return (f"{recipe.slots}-ship: {human_label} + {recipe.veteran_wingmen} veteran AI "
            f"{ai_label} (High skill), in the same flight. Use the wingman radio menu to command them.")
