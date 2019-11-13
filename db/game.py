#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from neomodel import StructuredNode, StringProperty, RelationshipFrom, RelationshipTo, IntegerProperty, \
    BooleanProperty, UniqueIdProperty

from db.task import Task


class Point(StructuredNode):
    """
    'abstract' base
    """
    pid = UniqueIdProperty()
    title = StringProperty()


class Waypoint(Point):
    """
    Waypoints are all potential steps on a path from start to finish.
    Each waypoint can have tasks, and can have destinations
    """
    # descriptions are used for transition texts on links connecting waypoints
    description = StringProperty()
    # text contains the text to be displayed
    text = StringProperty()
    # media to be rendered (expecting url's here)
    media = StringProperty()
    # if there is a limit for showing this waypoint
    time_limit = IntegerProperty()
    # if this waypoint can only be reached if a certain amount of money is available
    money_limit = IntegerProperty()
    # show the timer if a time-limit has been set
    timer_visible = BooleanProperty()
    # tasks that need to be solved (for 'other' destinations to become available)
    tasks = RelationshipFrom('Task', 'TASKS')
    # a game level associated with the waypoint
    level = RelationshipTo('Level', 'LEVEL')
    # destination(s) available without solving tasks
    destination = RelationshipTo('Waypoint', 'DESTINATION')

    def is_finish(self):
        """
        A finish is defined as a Waypoint without destinations
        :return: boolean
        """
        if (not self.destination or len(self.destination) == 0) and (not self.tasks or len(self.tasks) == 0):
            return True
        return False


class Start(Point):
    """
    Special waypoint indicating a starting position in a game
    """
    # text contains the text to be displayed
    prolog = StringProperty()
    # media to be rendered (expecting url's here)
    media = StringProperty()
    destination = RelationshipTo('Waypoint', 'DESTINATION')


class Level(StructuredNode):
    lid = UniqueIdProperty()
    title = StringProperty()
    icon = StringProperty()


class Game(StructuredNode):
    gid = UniqueIdProperty()
    title = StringProperty(unique_index=True)
    image = StringProperty()
    start = RelationshipTo('Start', 'START')
