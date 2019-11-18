#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import pytest

from model.game import Game, Waypoint
from model.inputs import TextInput
from model.instance import SinglePlayerGame
from model.player import Player, PlayerIllegalMoveException
from model.task import TextTask


def test_simple_graph_generation():
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    end = Waypoint(game.graph, 'end')
    start.add_destination(end)
    assert len(game.graph.nodes) == 2
    assert len(game.graph.edges) == 1
    assert not game.start_is_set()


def test_adding_task_adds_path():
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    end = Waypoint(game.graph, 'end')
    task = TextTask('test description', 'answer')
    start.add_destination(end, task)
    game.set_start(start)
    assert len(game.graph.nodes) == 2
    assert len(game.graph.edges) == 1
    assert game.start_is_set()


def test_identify_player_path():
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    w2 = Waypoint(game.graph, 'w2')
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    task = TextTask('test task', 'answer')
    w1.add_destination(w2, task)
    w2.add_destination(end)
    game.set_start(start)
    player = Player('test', 'player')
    instance = SinglePlayerGame(game, player, 'testy', 'mctestpants')
    assert len(instance.player_state.path) == 1
    assert instance.player_state.path[0] == start
    assert w1 in instance.player_state.available_moves() and w2 not in instance.player_state.available_moves()
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_state.move_to(end)
    instance.player_state.move_to(w1)
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_state.move_to(start)
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_state.move_to(w2)
    inp = TextInput(w2, 'answer')
    assert w1 not in instance.player_state.available_moves() and w2 in instance.player_state.available_moves(inp)
    instance.player_state.move_to(w2, inp)
    assert not instance.player_state.is_finished()
    instance.player_state.move_to(end)
    assert instance.player_state.current_position() == end
    assert instance.player_state.is_finished()
