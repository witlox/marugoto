#!/usr/bin/env python
# -*- coding: utf-8 -*-#
from datetime import datetime

from model.dialog import Dialog, Interaction


class PlayerStateException(Exception):
    """Player is in an undefined state"""
    pass


class PlayerIllegalMoveException(Exception):
    """Player wants to make an illegal move"""
    pass


class Player(object):
    """
    Representation of users
    """
    def __init__(self, email: str, password: str):
        """
        Users currently require an email and a password, later we may include shibboleth
        :param email: email address of the player
        :param password: hashed password of the player
        """
        self.email = email
        self.password = password


class PlayerState(object):
    """
    Relationship between players and their game state
    Any player can have multiple states for a given game
    """
    def __init__(self, player: Player, first_name: str, last_name: str, game_instance):
        """
        The player state is their in game persona
        :param player: corresponding player
        :param first_name: first name pseudonym
        :param last_name: last name pseudonym
        :param game_instance: instance of the game associated with this state
        """
        self.player = player
        self.first_name = first_name
        self.last_name = last_name
        self.game_instance = game_instance
        self.path = [game_instance.game.start]
        self.dialogs = {}
        self.inventory = {}

    def add_dialog_response(self, npc, interaction, response):
        """
        log a response to an NPC interaction into your dialogs
        :param npc: non-playable character
        :param interaction: interaction target
        :param response: response to log
        """
        if npc not in self.dialogs.keys():
            self.dialogs[npc] = []
        self.dialogs[npc].append((interaction, response))

    def add_stuff(self, key, stuff):
        self.inventory[datetime.utcnow()](key, stuff)

    def available_moves(self, answer=None):
        """
        show my available moves
        :param answer: optional input for a task
        """
        current = next(iter(n for n in self.game_instance.game.graph.nodes if n == self.path[-1]), None)
        if not current:
            raise PlayerStateException(f'Could not determine current position on path for {self.first_name} '
                                       f'{self.last_name} ({self.player.email} -> {self.game_instance.title}')
        moves = []
        for successor in self.game_instance.game.graph.successors(current):
            # validate answers to return blocked waypoints
            for task in current.tasks:
                if task.destination and task.solve(answer):
                    moves.append(task.destination)
            # check NPC interactions to return waypoints which require dialog
            for interaction in current.interactions:
                for npc in self.game_instance.npc_states:
                    if interaction.destination and interaction in npc.get_player_dialog(self):
                        moves.append(interaction.destination)
            # and everything else
            if successor not in [d.destination for d in current.tasks if d.destination] + [d.destination for d in current.interactions if d.destination]:
                moves.append(successor)
        return set(moves)

    def available_path(self):
        """
        show my available path
        """
        current = next(iter(n for n in self.game_instance.game.graph.nodes if n == self.path[-1]), None)
        if not current:
            raise PlayerStateException(f'Could not determine current position on path for {self.first_name} '
                                       f'{self.last_name} ({self.player.email} -> {self.game_instance.game.title}')
        return current.all_path_nodes()

    def current_position(self):
        return self.path[-1]

    def move_to(self, waypoint, answer=None):
        """
        (generator) move to next waypoint
        :param waypoint: next step on path
        :param answer: optional input for task
        :return: dict of {npc, [interactions]} for any given NPC
        """
        if waypoint not in self.available_moves(answer):
            raise PlayerIllegalMoveException(f'Cannot move from {self.path[-1].title} to {waypoint.title}')
        self.path.append(waypoint)

        interactions = {}
        for npc in self.game_instance.npc_states:
            interactions[npc] = npc.available_interaction(self, answer)
        return interactions

    def is_finished(self):
        return self.path[-1].is_finish()


class NonPlayableCharacter(object):
    """
    Non playable characters can be used in multiple games
    """
    def __init__(self,
                 first_name: str,
                 last_name: str,
                 salutation: str = None,
                 mail: str = None,
                 image: object = None):
        self.first_name = first_name
        self.last_name = last_name
        self.salutation = salutation
        self.mail = mail
        self.image = image

    def create(self, game_instance, dialog):
        return NonPlayableCharacterState(self.first_name, self.last_name, game_instance, dialog, self.salutation, self.mail, self.image)


class NonPlayableCharacterState(NonPlayableCharacter):
    def __init__(self,
                 first_name: str,
                 last_name: str,
                 game_instance,
                 dialog: Dialog,
                 salutation: str = None,
                 mail: str = None,
                 image: object = None):
        if not dialog.start_is_set():
            raise PlayerStateException(f'Dialog start not set for NPC {first_name} {last_name}')
        super().__init__(first_name, last_name, salutation, mail, image)
        self.game_instance = game_instance
        self.dialog = dialog
        self.paths = {}

    def add_player(self, instance: PlayerState):
        """
        when adding a new player to the game, initialize the NPC state for the given player
        :param instance: player state
        """
        self.paths[instance] = []

    def remove_player(self, instance: PlayerState):
        """
        remove the player state for the NPC
        :param instance: player state
        """
        self.paths.pop(instance, None)

    def update_player_dialog(self, instance: PlayerState, interaction: Interaction, answer):
        """
        add an interaction to the dialog
        :param instance: player state
        :param interaction: interaction to add
        :param answer: response to the interaction
        """
        instance.add_dialog_response(self, interaction, answer)
        next_interaction = self.available_interaction(instance, answer)
        if next_interaction:
            self.paths[instance].append(next_interaction)

    def get_player_dialog(self, instance: PlayerState):
        """
        get the current player dialog state
        :param instance: player state
        :return: Interactions between player and npc
        """
        return self.paths[instance]

    def available_interaction(self, instance: PlayerState, answer=None):
        """
        show NPC available interactions for a given player
        :param instance: player state
        :param answer: optional answer for a given NPC task (like respond to email)
        :return Interaction (or None)
        """
        if not self.paths[instance]:
            if instance.current_position() in self.dialog.start.waypoints:
                self.paths[instance] = [self.dialog.start]
                return self.dialog.start
        current = next(iter(n for n in self.dialog.graph.nodes if n == self.paths[instance][-1]), None)
        if not current:
            raise PlayerStateException(f'Dialog position error for {instance.first_name} {instance.last_name} '
                                       f'({instance.player.email})')
        for successor in self.dialog.graph.successors(current):
            if successor.waypoints and instance.path[-1] in successor.waypoints:
                if successor.task and successor.task.solve(answer):
                    return successor
                elif not successor.task:
                    return successor
            elif not successor.waypoints:
                if successor.task and successor.task.solve(answer):
                    return successor
                elif not successor.task:
                    return successor
        return None
