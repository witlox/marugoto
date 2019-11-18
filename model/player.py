#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from model.game import Waypoint


class PlayerStateException(Exception):
    """Player is in an undefined state"""
    pass


class PlayerIllegalMoveException(Exception):
    """Player wants to make an illegal move"""
    pass


class Player(object):
    def __init__(self, mail: str, password: str):
        self.mail = mail
        self.password = password


class PlayerState(object):
    """
    Relationship between players and their game state
    Any player can have multiple states for a given game
    """
    def __init__(self, player: Player, first_name: str, last_name: str, game_instance, start: Waypoint):
        self.player = player
        self.first_name = first_name
        self.last_name = last_name
        self.game = game_instance
        self.solutions = []
        self.notes = []
        self.path = [start]

    def add_note(self, note):
        self.notes.append(note)

    def add_solution(self, solution):
        self.solutions.append(solution)

    def available_moves(self, inp=None) -> [Waypoint]:
        """
        show my available moves
        :param inp: optional input for a task
        """
        current = next(iter(n for n in self.game.game.graph.nodes if n == self.path[-1]), None)
        if not current:
            raise PlayerStateException(f'Could not determine current position on path for ${self.first_name} '
                                       f'${self.last_name} (${self.player.mail} -> ${self.game.game.title}')
        return current.destinations(inp)

    def current_position(self) -> Waypoint:
        return self.path[-1]

    def move_to(self, waypoint, inp=None):
        """
        move to next waypoint
        :param waypoint: next step on path
        :param inp: optional input for task
        """
        if waypoint not in self.available_moves(inp):
            raise PlayerIllegalMoveException(f'Cannot move from ${self.path[-1].title} to ${waypoint.title}')
        self.solutions.append(inp)
        self.path.append(waypoint)

    def is_finished(self):
        return self.path[-1].is_finish()
