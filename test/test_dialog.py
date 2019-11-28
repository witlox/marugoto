#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import pytest

from model.dialog import Mail, Dialog
from model.game import Game, Waypoint
from model.player import Player, NonPlayableCharacterState, PlayerStateException, NonPlayableCharacter


def test_npc_interaction():
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    w1.add_destination(end)
    game.set_start(start)
    instance = game.create_new_game()
    npc_dialog = Dialog()
    ds = Mail(npc_dialog.graph, 'test subject', 'test body')
    with pytest.raises(PlayerStateException):
        NonPlayableCharacterState('test', 'npc', game, npc_dialog)
    npc_dialog.set_start(ds, w1)
    instance.add_non_playable_character(NonPlayableCharacter('test', 'npc').create(instance, npc_dialog))
    instance.add_player(Player('test', 'player'), 'testy', 'mctestpants')
    assert len(instance.npc_states) == 1
    assert ds not in [k for k, _ in instance.player_states[0].inventory.values()]
    interactions = instance.player_states[0].move_to(w1)
    assert len(interactions.keys()) == 1 and len(interactions.values()) == 1


def test_npc_required_response():
    npc_dialog = Dialog()
    ds1 = Mail(npc_dialog.graph, 'test subject 1', 'test body 1')
    ds2 = Mail(npc_dialog.graph, 'test subject 2', 'test body 2')
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    end = Waypoint(game.graph, 'end')
    game.set_start(start)
    npc_dialog.set_start(ds1, w1)
    start.add_destination(w1)
    ds1.add_follow_up(ds2, end)
    w1.add_destination(end, interaction=ds2)
    instance = game.create_new_game()
    npc = NonPlayableCharacter('test', 'npc').create(instance, npc_dialog)
    instance.add_non_playable_character(npc)
    instance.add_player(Player('test', 'player'), 'testy', 'mctestpants')
    assert len(instance.player_states[0].available_moves()) == 1
    interaction = instance.player_states[0].move_to(w1)
    assert len(instance.player_states[0].available_moves()) == 0
    npc.update_player_dialog(instance.player_states[0], interaction, 'mail response')
    assert len(instance.player_states[0].available_moves()) == 1
    assert instance.player_states[0].move_to(end)
