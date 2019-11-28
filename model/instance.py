#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from datetime import datetime

from model.player import PlayerState, Player, NonPlayableCharacterState


class GameInvalidException(Exception):
    """Raised when a game has no start"""
    pass


class GameInstance(object):
    """Instance of a Game"""
    def __init__(self,
                 game,
                 name: str = None,
                 game_master: Player = None,
                 starts_at: datetime = None,
                 ends_at: datetime = None):
        """
        Instance of a game
        :param game: associated explicit game
        :param name: name of the game instance
        :param game_master: player hosting the game
        :param starts_at: utc start timestamp
        :param ends_at: utc end timestamp
        """
        if not game.start_is_set():
            raise GameInvalidException(f'Start not set for ${game.title}')
        self.created_at = datetime.utcnow()
        self.game = game
        self.name = name
        self.game_master = game_master
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.npc_states = []
        self.player_states = []

    def add_non_playable_character(self, npc: NonPlayableCharacterState):
        """
        add NPC to a multiplayer game
        :param npc: our non-playable character
        """
        self.npc_states.append(npc)

    def add_player(self, player: Player, first_name: str, last_name: str):
        """
        add player to a multiplayer game
        :param player: player to add
        :param first_name: first name pseudonym
        :param last_name: last name pseudonym
        """
        instance = PlayerState(player, first_name, last_name, self)
        self.player_states.append(instance)
        for npc in self.npc_states:
            npc.add_player(instance)

    def remove_player(self, player: Player):
        """
        remove player from an existing multiplayer game
        :param player: player to remove
        """
        instance = next(iter([i for i in self.player_states if i.player == player]), None)
        if instance:
            for npc in self.npc_states:
                npc.remove_player(instance)
            self.player_states.remove(instance)
