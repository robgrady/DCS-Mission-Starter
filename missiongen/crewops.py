"""Crew Ops machinery: player-paced backseat missions.

The backseat contract: THE MISSION FLIES THE JET; THE PLAYER RUNS THE MISSION.
Scenarios are chains of task gates driven by the F10 crew menu (radio items set
flags), advanced by real events (unit dead, zone entry), with immediate text
feedback. No stopwatch scripting — the player sets the pace.

Flag space: 200+ for crew-menu commands, 300+ for internal state.
"""
from dcs.triggers import TriggerOnce, TriggerCondition
from dcs.condition import FlagIsTrue, GroupDead, TimeAfter, FlagEquals
from dcs.action import (AddRadioItem, SetFlagValue, SetFlag,
                        MessageToCoalition, RemoveRadioItem)


class CrewFlow:
    """Builds an event-driven task flow: crew menu commands, gates, feedback."""

    def __init__(self, m, difficulty="qualified"):
        self.m = m
        self.difficulty = difficulty
        self._flag = 200

    def next_flag(self):
        self._flag += 1
        return self._flag

    def _s(self, text):
        """Mission texts must be translation Strings, not plain str."""
        return self.m.string(text)

    def _trigger(self, comment, conditions, actions, once=True):
        t = TriggerOnce(comment=comment)
        for c in conditions:
            t.rules.append(c)
        for a in actions:
            t.actions.append(a)
        self.m.triggerrules.triggers.append(t)
        return t

    def add_command(self, menu_text, actions, after_flag=None, feedback=None,
                    hint=None):
        """A crew-menu command: F10 item -> flag -> actions (+ feedback msg).
        after_flag gates when the menu item appears (progressive disclosure)."""
        flag = self.next_flag()
        # menu item appears at start, or when the gating flag is set
        show_cond = [FlagIsTrue(after_flag)] if after_flag else [TimeAfter(5)]
        self._trigger(f"menu: {menu_text}", show_cond,
                      [AddRadioItem(radiotext=self._s(menu_text), flag=flag, value=1)])
        acts = list(actions)
        if feedback:
            acts.append(MessageToCoalition(text=self._s(feedback), seconds=12))
        self._trigger(f"exec: {menu_text}", [FlagIsTrue(flag)], acts)
        # trainee difficulty: prompt what to do when the command becomes available
        if hint and self.difficulty == "trainee":
            self._trigger(f"hint: {menu_text}", show_cond,
                          [MessageToCoalition(text=self._s(f"[CREW HINT] {hint}"), seconds=15)])
        return flag

    def on_group_dead(self, group_name, actions, feedback=None):
        acts = list(actions)
        if feedback:
            acts.append(MessageToCoalition(text=self._s(feedback), seconds=15))
        self._trigger(f"event: {group_name} destroyed",
                      [GroupDead(group_name)], acts)

    def on_flag(self, flag, actions, feedback=None, comment=""):
        acts = list(actions)
        if feedback:
            acts.append(MessageToCoalition(text=self._s(feedback), seconds=15))
        self._trigger(comment or f"on flag {flag}", [FlagIsTrue(flag)], acts)

    def message_at_start(self, text, seconds=20):
        self._trigger("mission start message", [TimeAfter(10)],
                      [MessageToCoalition(text=self._s(text), seconds=seconds)])
