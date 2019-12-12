#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from uuid import uuid4

import networkx as nx

from model.instance import GameInstance
from model.player import NonPlayableCharacter


class Level(object):
    def __init__(self, title: str, icon=None):
        """
        A level in a game
        :param title: title of the level
        :param icon: icon associated with the level
        """
        self.title = title
        self.icon = icon


class Waypoint(object):
    """
    Waypoints are all potential steps on a path from start to finish.
    """
    def __init__(self,
                 graph: nx.DiGraph,
                 title: str,
                 description: str = None,
                 time_limit: float = 0.0,
                 money_limit: float = 0.0,
                 budget_modification: float = 0.0,
                 items=None,
                 timer_visible: bool = False,
                 level: Level = None):
        """
        Each Waypoint can have tasks, and can have destinations.
        :param graph: directed graph that contains this waypoint
        :param title: name of the waypoint
        :param description: descriptions are used for transition texts on links connecting waypoints
        :param time_limit: if there is a limit for showing this waypoint (in seconds)
        :param money_limit: if this waypoint can only be reached if a certain amount of money is available
        :param budget_modification: modify budget if waypoint is reached
        :param items: items to add to inventory if waypoint is reached
        :param timer_visible: show the timer if a time-limit has been set
        :param level: a game level associated with the waypoint
        """
        self.id = uuid4()
        self.graph = graph
        self.title = title
        self.description = description
        self.time_limit = time_limit
        self.money_limit = money_limit
        self.budget_modification = budget_modification
        self.timer_visible = timer_visible
        self.level = level
        self.items = items
        # tasks that need to be solved destinations to become available
        self.tasks = []
        # required NPC interactions for this destination to be available
        self.interactions = []
        # add oneself to the graph as node
        self.graph.add_node(self)

    def __eq__(self, other):
        if self and other and isinstance(other, Waypoint):
            return self.id == other.id
        return False

    def __hash__(self):
        return self.id.__hash__()

    def __str__(self):
        return self.title

    def __repr__(self):
        return f'Waypoint: ({self.title}) ({self.description})'

    def add_destination(self, waypoint, weight: float = None):
        """
        add a destination waypoint
        :param waypoint: destination
        :param weight: potential edge weight
        """
        if not weight:
            self.graph.add_edge(self, waypoint)
        else:
            self.graph.add_edge(self, waypoint, weight=weight)

    def add_task(self, task):
        """
        add a task
        :param task: task that needs to be solved for this waypoint
        """
        if task.destination:
            self.graph.add_edge(self, task.destination)
        self.tasks.append(task)

    def add_interaction(self, interaction):
        """
        add an interaction
        :param interaction: specific interaction with NPC
        """
        if interaction.destination:
            self.graph.add_edge(self, interaction.destination)
        self.interactions.append(interaction)

    def all_path_nodes(self):
        """
        return all possible waypoints from here
        :return: list of waypoints
        """
        return nx.dfs_tree(self.graph, self)

    def is_finish(self) -> bool:
        """
        A finish is defined as a Waypoint without destinations
        """
        if len(list(self.graph.successors(self))) == 0:
            return True
        return False


class Game(object):
    """
    Main container for our Game graph
    """
    def __init__(self, title: str, image=None, start: Waypoint = None, energy: float = None):
        """
        A game is a Directed Acyclic Graph of [Waypoint]
        :param title: title of the game
        :param image: game image
        :param start: starting waypoint of the game
        :param energy: total amount of energy for a game
        """
        self.graph = nx.DiGraph()
        self.title = title
        self.image = image
        self.start = start
        self.energy = energy
        self.npcs = []

    def set_start(self, waypoint):
        """
        Starting point of the game
        :param waypoint: starting waypoint
        """
        self.start = waypoint

    def start_is_set(self) -> bool:
        """
        check if start is set
        :return: bool
        """
        return self.start is not None

    def add_non_playable_character(self, npc: NonPlayableCharacter):
        """
        add NPC to a multiplayer game
        :param npc: our non-playable character
        """
        self.npcs.append(npc)

    def create_new_game(self, name: str = None, game_master=None, starts_at=None, ends_at=None):
        """
        create a new instance of this game
        :param name: name of the game
        :param game_master: player that is supervising
        :param starts_at: starting time for the game
        :param ends_at: end time when the game will stop
        :return: GameInstance
        """
        return GameInstance(self, name, game_master, starts_at, ends_at)
