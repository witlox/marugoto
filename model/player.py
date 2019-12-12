#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from datetime import datetime, timedelta
from math import isclose
from uuid import UUID, uuid4

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
        self.id = uuid4()
        self.email = email
        self.password = password


class PlayerState(object):
    """
    Relationship between players and their game state
    Any player can have multiple states for a given game
    """
    def __init__(self, player, first_name: str, last_name: str, game_instance, initial_budget:float = 0.0):
        """
        The player state is their in game persona
        :param player: corresponding player (or their email)
        :param first_name: first name pseudonym
        :param last_name: last name pseudonym
        :param game_instance: instance of the game associated with this state
        """
        self.player = player
        self.first_name = first_name
        self.last_name = last_name
        self.game_instance = game_instance
        self.budget = initial_budget
        if game_instance and game_instance.game:
            self.energy = game_instance.game.energy
            self.path = [(datetime.utcnow(), game_instance.game.start)]
        else:
            self.energy = None
            self.path = []
        self.dialogs = {}
        self.inventory = {}

    def add_dialog_response(self, npc, interaction, response):
        """
        log a response to an NPC interaction into your dialogs
        :param npc: non-playable character
        :param interaction: interaction target
        :param response: response to log
        """
        self.budget += interaction.budget_modification
        if npc not in self.dialogs.keys():
            self.dialogs[npc] = []
        self.dialogs[npc].append((datetime.utcnow(), interaction, response))

    def add_stuff(self, key, stuff):
        """
        add stuff to the inventory
        :param key: id hex of the thing holding the item
        :param stuff: item to add to inventory
        """
        dt = datetime.utcnow()
        if dt in self.inventory.keys():
            self.inventory[dt].append((key, stuff))
        else:
            self.inventory[dt] = [(key, stuff)]

    def available_moves(self, answer=None):
        """
        show my available moves
        :param answer: optional input for a task
        """
        previous_move_stamp = self.path[-1][0]
        current = next(iter(n for n in self.game_instance.game.graph.nodes if n == self.current_position()), None)
        if not current:
            raise PlayerStateException(f'Could not determine current position on path for {self.first_name} '
                                       f'{self.last_name} ({self.player.email} -> {self.game_instance.title}')
        moves = []
        for successor in self.game_instance.game.graph.successors(current):
            # check if there is a time limit we've exceeded
            if not isclose(successor.time_limit, 0.0) and datetime.utcnow() > previous_move_stamp + timedelta(seconds=successor.time_limit):
                continue
            # check if there is a budget requirement we don't meet
            if not isclose(successor.money_limit, 0.0) and self.budget < successor.money_limit:
                continue
            # check if there is an energy requirement we don't meet
            if self.energy and 'weight' in self.game_instance.game.graph.edges[current, successor] and self.game_instance.game.graph.edges[current, successor]['weight']:
                if self.energy - self.game_instance.game.graph.edges[current, successor]['weight'] < 0:
                    continue
            # validate answers to return blocked waypoints
            for task in current.tasks:
                if not isclose(task.time_limit, 0.0) and datetime.utcnow() > previous_move_stamp + timedelta(seconds=task.time_limit):
                    continue
                if not isclose(task.money_limit, 0.0) and self.budget < task.money_limit:
                    continue
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
        current = next(iter(n for n in self.game_instance.game.graph.nodes if n == self.current_position()), None)
        if not current:
            raise PlayerStateException(f'Could not determine current position on path for {self.first_name} '
                                       f'{self.last_name} ({self.player.email} -> {self.game_instance.game.title}')
        return current.all_path_nodes()

    def current_position(self):
        return self.path[-1][1]

    def move_to(self, waypoint, answer=None):
        """
        (generator) move to next waypoint
        :param waypoint: next step on path
        :param answer: optional input for task
        :return: dict of {npc, [interactions]} for any given NPC
        """
        if self.game_instance.starts_at and datetime.utcnow() < self.game_instance.starts_at:
            raise PlayerStateException(f'game has not started yet, wait till {self.game_instance.starts_at} (UTC)')
        if self.game_instance.ends_at and datetime.utcnow() > self.game_instance.ends_at:
            raise PlayerStateException(f'game has ended')

        if waypoint not in self.available_moves(answer):
            raise PlayerIllegalMoveException(f'Cannot move from {self.current_position().title} to {waypoint.title}')

        if waypoint.items:
            for item in waypoint.items:
                self.add_stuff(waypoint, item)
        for task in waypoint.tasks:
            if task.solve(answer):
                self.budget += task.budget_modification
            if task.items and task.solve(answer):
                for item in task.items:
                    self.add_stuff(task, item)
        self.budget += waypoint.budget_modification

        if self.energy and 'weight' in self.game_instance.game.graph.edges[self.current_position(), waypoint] and \
                self.game_instance.game.graph.edges[self.current_position(), waypoint]['weight']:
            self.energy -= self.game_instance.game.graph.edges[self.current_position(), waypoint]['weight']
        self.path.append((datetime.utcnow(), waypoint))

        interactions = {}
        for npc in self.game_instance.npc_states:
            interactions[npc] = npc.available_interaction(self, answer)
        return interactions

    def is_finished(self):
        return self.current_position().is_finish()


class NonPlayableCharacter(object):
    """
    Non playable characters can be used in multiple games
    """
    def __init__(self,
                 first_name: str,
                 last_name: str,
                 dialog: Dialog,
                 salutation: str = None,
                 mail: str = None,
                 image: object = None):
        if not dialog.start_is_set():
            raise PlayerStateException(f'Dialog start not set for NPC {first_name} {last_name}')
        self.first_name = first_name
        self.last_name = last_name
        self.dialog = dialog
        self.salutation = salutation
        self.mail = mail
        self.image = image

    def __eq__(self, other):
        if self and other and (isinstance(other, NonPlayableCharacterState) or isinstance(other, NonPlayableCharacter)):
            return self.first_name == other.first_name and self.last_name == other.last_name
        return False

    def __hash__(self):
        return hash(f'{self.first_name} {self.last_name}')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def __repr__(self):
        return f'NPC: ({self.first_name}) ({self.last_name})'

    def create(self, game_instance):
        return NonPlayableCharacterState(self.first_name, self.last_name, game_instance, self.dialog, self.salutation, self.mail, self.image)


class NonPlayableCharacterState(NonPlayableCharacter):
    def __init__(self,
                 first_name: str,
                 last_name: str,
                 game_instance,
                 dialog,
                 salutation: str = None,
                 mail: str = None,
                 image: object = None):
        super().__init__(first_name, last_name, dialog, salutation, mail, image)
        self.game_instance = game_instance
        self.paths = {}

    def add_player(self, instance: PlayerState):
        """
        when adding a new player to the game, initialize the NPC state for the given player
        :param instance: player state
        """
        self.paths[instance] = [(datetime.utcnow(), self.dialog.start)]

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
            self.paths[instance].append((datetime.utcnow(), next_interaction))
            if next_interaction.task and next_interaction.task.solve(answer) and next_interaction.task.items:
                for item in next_interaction.task.items:
                    instance.add_stuff(next_interaction.task, item)
            if next_interaction.items:
                for item in next_interaction.items:
                    instance.add_stuff(next_interaction, item)

    def get_player_dialog(self, instance: PlayerState):
        """
        get the current player dialog state
        :param instance: player state
        :return: Interactions between player and npc
        """
        return [i[1] for i in self.paths[instance]]

    def available_interaction(self, instance: PlayerState, answer=None):
        """
        show NPC available interactions for a given player
        :param instance: player state
        :param answer: optional answer for a given NPC task (like respond to email)
        :return Interaction (or None)
        """
        previous = self.paths[instance][-1]
        current = next(iter(n for n in self.dialog.graph.nodes if n == previous[1]), None)
        if not current:
            raise PlayerStateException(f'Dialog position error for {instance.first_name} {instance.last_name} '
                                       f'({instance.player.email})')
        for successor in self.dialog.graph.successors(current):
            if (isclose(successor.money_limit, 0.0) or successor.money_limit < instance.budget) and (isclose(successor.time_limit, 0.0) or datetime.now() < previous[0] + timedelta(seconds=successor.time_limit)):
                if successor.waypoints and instance.path[-1][1] in successor.waypoints:
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
