#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import networkx as nx

from model.game import Waypoint, Level


class Text(Waypoint):
    def __init__(self,
                 graph: nx.DiGraph,
                 title: str,
                 content: str,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 timer_visible: bool = None,
                 level: Level = None):
        super().__init__(graph, title, description, time_limit, money_limit, timer_visible, level)
        self.content = content


class Image(Waypoint):
    def __init__(self,
                 graph: nx.DiGraph,
                 title: str,
                 image: object,
                 caption: str,
                 zoomable: bool = False,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 timer_visible: bool = None,
                 level: Level = None):
        super().__init__(graph, title, description, time_limit, money_limit, timer_visible, level)
        self.image = image
        self.caption = caption
        self.zoomable = zoomable


class Video(Waypoint):
    def __init__(self,
                 graph: nx.DiGraph,
                 title: str,
                 fragment: object,
                 caption: str,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 timer_visible: bool = None,
                 level: Level = None):
        super().__init__(graph, title, description, time_limit, money_limit, timer_visible, level)
        self.video = fragment
        self.caption = caption


class Audio(Waypoint):
    def __init__(self,
                 graph: nx.DiGraph,
                 title: str,
                 fragment: object,
                 description: str = None,
                 time_limit: float = None,
                 money_limit: float = None,
                 timer_visible: bool = None,
                 level: Level = None):
        super().__init__(graph, title, description, time_limit, money_limit, timer_visible, level)
        self.image = fragment
