#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import pytest

from model.game import Game, Waypoint
from model.player import Player, PlayerIllegalMoveException
from model.task import Task


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
    task = Task(end, 'test description', 'test text', 'answer')
    start.add_task(task)
    game.set_start(start)
    assert len(game.graph.nodes) == 2
    assert len(game.graph.edges) == 1
    assert game.start_is_set()


def test_identify_player_path():
    """
    start
      |
      w1
      |  <- task answer required before transition becomes available
      w2
      |
      end
    """
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    w2 = Waypoint(game.graph, 'w2', items=['some item'])
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    task = Task(w2, 'test description', 'test text', 'answer')
    w1.add_task(task)
    w2.add_destination(end)
    game.set_start(start)
    instance = game.create_new_game()
    player = Player('test', 'player')
    instance.add_player(player, 'testy', 'mctestpants')
    assert len(instance.player_states[0].path) == 1
    assert instance.player_states[0].path[0][1] == start
    assert w1 in instance.player_states[0].available_moves()
    assert w2 in instance.player_states[0].available_path()
    # not allowed to skip to end
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_states[0].move_to(end)
    instance.player_states[0].move_to(w1)
    # no backsies
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_states[0].move_to(start)
    # w2 is blocked from w1
    with pytest.raises(PlayerIllegalMoveException):
        instance.player_states[0].move_to(w2)
    answer = 'answer'
    assert len(instance.player_states[0].inventory) == 0
    instance.player_states[0].move_to(w2, answer)
    assert not instance.player_states[0].is_finished()
    assert len(instance.player_states[0].inventory) == 1
    instance.player_states[0].move_to(end)
    assert instance.player_states[0].current_position() == end
    assert instance.player_states[0].is_finished()
