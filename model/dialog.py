#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from uuid import uuid4

import networkx as nx

from model.task import Task


class Interaction(object):
    """
    Interaction between player and npc, the idea is that interactions can have waypoints associated with them,
    once a waypoint is reached, dialog will occur till a task is set (and will continue when the task is solved),
    or the dialog will occur till a next interaction is defined that has a specific set of waypoints associated with
    it.
    """
    def __init__(self,
                 graph: nx.DiGraph,
                 description: str,
                 money_limit: float,
                 time_limit: float,
                 task: Task = None,
                 destination=None):
        """
        Interactions are nodes in a graph, which can be followed up by other interactions
        :param graph: directed graph that contains this interaction
        :param description: description of the interaction which is shown as a text for ancestor interactions
        :param money_limit: interaction only available if a player has a given amount of money
        :param task: task that needs to be solved for dialog to continue
        :param destination: destination that becomes available after completing this interaction
        """
        self.id = uuid4()
        self.graph = graph
        self.description = description
        self.money_limit = money_limit
        self.time_limit = time_limit
        self.waypoints = []
        self.graph.add_node(self)
        self.task = task
        self.destination = destination

    def __eq__(self, other):
        if self and other and isinstance(other, Interaction):
            return self.id == other.id
        return False

    def __hash__(self):
        return self.id.__hash__()

    def __str__(self):
        return self.description

    def __repr__(self):
        return f'Interaction: ({self.description})'

    def add_follow_up(self, interaction, waypoints=None):
        """
        add a followup to an interaction, possibly associated with (a) specific waypoint(s)
        :param interaction: the follow up
        :param waypoints: only available at a given waypoints
        """
        self.graph.add_edge(self, interaction)
        if waypoints and isinstance(waypoints, list):
            for waypoint in waypoints:
                self.waypoints.append(waypoint)
        elif waypoints:
            self.waypoints.append(waypoints)

    def follow_ups(self, waypoint=None):
        """
        return all followups available from this interaction
        :param waypoint: current waypoint
        :return: list of interactions
        """
        for successor in self.graph.successors(self):
            if waypoint and waypoint in self.waypoints:
                yield successor
            elif not self.waypoints:
                yield successor

    def all_path_nodes(self):
        """
        return all possible interactions from here
        :return: list of interactions
        """
        return nx.dfs_tree(self.graph, self)

    def have_task(self) -> bool:
        """
        check if a task exists for this interaction
        :return: true/false
        """
        return self.task is not None


class Speech(Interaction):
    def __init__(self,
                 graph: nx.DiGraph,
                 content: str,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 task: Task = None,
                 destination=None):
        super().__init__(graph, description, time_limit, money_limit, task, destination)
        self.content = content


class Mail(Interaction):
    def __init__(self,
                 graph: nx.DiGraph,
                 subject: str,
                 body: str,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 task: Task = None,
                 destination=None):
        super().__init__(graph, description, time_limit, money_limit, task, destination)
        self.subject = subject
        self.body = body


class Dialog(object):
    """
    Main container for dialogs between a player and a NPC
    """
    def __init__(self):
        """
        A dialog is a Directed Acyclic Graph of [Interaction]
        """
        self.graph = nx.DiGraph()
        self.start = None

    def set_start(self, interaction, waypoint):
        """Starting point of a dialog"""
        interaction.waypoints.append(waypoint)
        self.start = interaction

    def start_is_set(self) -> bool:
        return self.start is not None
