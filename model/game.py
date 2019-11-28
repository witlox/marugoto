#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from uuid import uuid4

import networkx as nx

from model.instance import GameInstance


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
                 time_limit: float = None,
                 money_limit: float = None,
                 timer_visible: bool = None,
                 level: Level = None):
        """
        Each Waypoint can have tasks, and can have destinations.
        :param graph: directed graph that contains this waypoint
        :param title: name of the waypoint
        :param description: descriptions are used for transition texts on links connecting waypoints
        :param time_limit: if there is a limit for showing this waypoint
        :param money_limit: if this waypoint can only be reached if a certain amount of money is available
        :param timer_visible: show the timer if a time-limit has been set
        :param level: a game level associated with the waypoint
        """
        self.id = uuid4()
        self.graph = graph
        self.title = title
        self.description = description
        self.time_limit = time_limit
        self.money_limit = money_limit
        self.timer_visible = timer_visible
        self.level = level
        # tasks that need to be solved destinations to become available
        self.tasks = {}
        # required NPC interactions for this destination to be available
        self.interactions = {}
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

    @staticmethod
    def instantiate(dictionary):
        """
        Regenerate object from Database Dict
        :param dictionary: dict from db
        :return: Waypoint
        """
        waypoint = Waypoint(**dictionary)
        waypoint.__dict__.update(dictionary)
        for k, v in dictionary.items():
            if isinstance(v, dict):
                waypoint.__dict__[k] = Waypoint.instantiate(v)
        return waypoint

    def add_destination(self, waypoint, task=None, interaction=None):
        """
        add a destination waypoint
        :param waypoint: destination
        :param task: task that needs to be solved for this destination to become available
        :param interaction: specific interaction with NPC required before this destination becomes available
        """
        self.graph.add_edge(self, waypoint)
        if task:
            self.tasks[waypoint] = task
        if interaction:
            self.interactions[waypoint] = interaction

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
    def __init__(self, title: str, image=None):
        """
        A game is a Directed Acyclic Graph of [Waypoint]
        :param title: title of the game
        :param image: game image
        """
        self.graph = nx.DiGraph()
        self.title = title
        self.image = image
        self.start = None

    def set_start(self, waypoint):
        """Starting point of the game"""
        self.start = waypoint

    def start_is_set(self):
        return self.start is not None

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
