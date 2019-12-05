#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import pytest
from pytest import fail

from model.dialog import Mail, Dialog
from model.game import Game, Waypoint
from model.player import Player, PlayerStateException, NonPlayableCharacter


def test_npc_interaction():
    """
      start
        |
        w1 <- dialog becomes available
        |
        end
    """
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    w1.add_destination(end)
    game.set_start(start)
    npc_dialog = Dialog()
    ds = Mail(npc_dialog.graph, 'test subject', 'test body')
    with pytest.raises(PlayerStateException):
        NonPlayableCharacter('test', 'npc', npc_dialog)
    npc_dialog.set_start(ds)
    npc_dialog.start.waypoints.append(w1)
    game.add_non_playable_character(NonPlayableCharacter('test', 'npc', npc_dialog))
    instance = game.create_new_game()
    instance.add_player(Player('test', 'player'), 'testy', 'mctestpants')
    assert len(instance.npc_states) == 1
    assert ds not in [k for k, _ in instance.player_states[0].inventory.values()]
    interactions = instance.player_states[0].move_to(w1)
    assert len(interactions.keys()) == 1 and len(interactions.values()) == 1


def test_npc_required_response():
    """
      start
        |
        w1 <- dialog becomes available
        |
        end <- blocked till dialog in phase 2 (ds2)
    """
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    end = Waypoint(game.graph, 'end')
    game.set_start(start)
    npc_dialog = Dialog()
    ds1 = Mail(npc_dialog.graph, 'test subject 1', 'test body 1')
    ds1.waypoints.append(w1)
    start.add_destination(w1)
    npc_dialog.set_start(ds1)
    ds2 = Mail(npc_dialog.graph, 'test subject 2', 'test body 2', destination=end)
    ds2.add_item('test item')
    ds1.add_follow_up(ds2, end)
    w1.add_interaction(ds2)
    npc = NonPlayableCharacter('test', 'npc', npc_dialog)
    game.add_non_playable_character(npc)
    instance = game.create_new_game()
    instance.add_player(Player('test', 'player'), 'testy', 'mctestpants')
    assert len(instance.player_states[0].available_moves()) == 1
    interaction = instance.player_states[0].move_to(w1)
    assert len(instance.player_states[0].available_moves()) == 0
    npc_instance = next(iter([n for n in instance.npc_states if n == npc]), None)
    if not npc_instance:
        assert fail('could not find npc instance in game instance')
    assert len(instance.player_states[0].inventory) == 0
    npc_instance.update_player_dialog(instance.player_states[0], interaction, 'mail response')
    assert len(instance.player_states[0].inventory) == 1
    assert len(instance.player_states[0].available_moves()) == 1
    assert instance.player_states[0].move_to(end)
