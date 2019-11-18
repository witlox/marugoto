#!/usr/bin/env python
# -*- coding: utf-8 -*-#


import networkx as nx


class Waypoint(object):
    """
    Waypoints are all potential steps on a path from start to finish.
    """

    def __init__(self, graph, title, description=None, text=None, media=None, time_limit=None, money_limit=None,
                 timer_visible=None, level=None):
        """
        Each Waypoint can have tasks, and can have destinations.
        :param graph: directed graph that contains this waypoint
        :param title: name of the waypoint
        :param description: descriptions are used for transition texts on links connecting waypoints
        :param text: text contains the text to be displayed
        :param media: media to be rendered (expecting url's here)
        :param time_limit: if there is a limit for showing this waypoint
        :param money_limit: if this waypoint can only be reached if a certain amount of money is available
        :param timer_visible: show the timer if a time-limit has been set
        :param level: a game level associated with the waypoint
        """
        self.graph = graph
        self.title = title
        self.description = description
        self.text = text
        self.media = media
        self.time_limit = time_limit
        self.money_limit = money_limit
        self.timer_visible = timer_visible
        self.level = level
        # tasks that need to be solved destinations to become available
        self.tasks = {}
        # our root node
        self.graph.add_node(self)

    def add_destination(self, waypoint, task=None):
        """
        add a destination waypoint
        :param waypoint: destination
        :param task: task that needs to be solved for this destination to become available
        """
        self.graph.add_edge(self, waypoint)
        if task:
            self.tasks[waypoint] = task

    def destinations(self, inp=None):
        """
        return all destinations available from this waypoint
        :param inp: input for (any) given tasks
        :return: list of waypoints
        """
        if inp:
            for waypoint in self.tasks.keys():
                if isinstance(self.tasks[waypoint], inp.input_association):
                    # todo: fuzzy matchers here
                    if self.tasks[waypoint].solution == inp.answer:
                        yield waypoint
        for successor in self.graph.successors(self):
            if successor not in self.tasks.keys():
                yield successor

    def is_finish(self) -> bool:
        """
        A finish is defined as a Waypoint without destinations
        """
        if len(list(self.graph.successors(self))) == 0:
            return True
        return False


class Level(object):

    def __init__(self, title: str, icon=None):
        """
        A level in a game
        :param title: title of the level
        :param icon: icon associated with the level
        """
        self.title = title
        self.icon = icon


class Game(object):

    def __init__(self, title: str, image=None):
        """
        A game is a directed acyclic graph of waypoints
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
