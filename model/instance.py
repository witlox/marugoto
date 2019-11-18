#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from datetime import datetime

from model.game import Game
from model.player import PlayerState, Player


class GameInvalidException(Exception):
    """Raised when a game has no start"""
    pass


class GameInstance(object):
    """Instance of a Game"""
    def __init__(self, game: Game):
        self.created_at = datetime.utcnow()
        self.game = game


class SinglePlayerGame(GameInstance):
    def __init__(self, game: Game, player: Player, first_name: str, last_name: str):
        """
        Single player game instance
        :param game: associated explicit game
        :param player: game player
        :param first_name: first name pseudonym
        :param last_name: last name pseudonym
        """
        if not game.start_is_set():
            raise GameInvalidException(f'Start not set for ${game.title}')
        super().__init__(game)
        self.player_state = PlayerState(player, first_name, last_name, self, game.start)


class MultiplayerGame(GameInstance):
    def __init__(self, game: Game, name: str, game_master: Player, starts_at: datetime, ends_at: datetime):
        """
        Multiplayer game
        :param game: associated explicit game
        :param name: name of the game instance
        :param game_master: player hosting the game
        :param starts_at: utc start timestamp
        :param ends_at: utc end timestamp
        """
        if not game.start_is_set():
            raise GameInvalidException(f'Start not set for ${game.title}')
        super().__init__(game)
        self.name = name
        self.game_master = game_master
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.player_states = []

    def add_player(self, player: Player, first_name: str, last_name: str):
        """
        add player to a multiplayer game
        :param player: player to add
        :param first_name: first name pseudonym
        :param last_name: last name pseudonym
        """
        instance = PlayerState(player, first_name, last_name, self.game, self.game.start)
        self.player_states.append(instance)

    def remove_player(self, player: Player):
        """
        remove player from an existing multiplayer game
        :param player: player to remove
        """
        instance = next(iter([i for i in self.player_states if i.player == player]), None)
        if instance:
            self.player_states.remove(instance)
