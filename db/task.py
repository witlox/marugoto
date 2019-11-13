#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from neomodel import StructuredNode, StringProperty, IntegerProperty, ArrayProperty, DateProperty, RelationshipTo, \
    ZeroOrOne, UniqueIdProperty


class Task(StructuredNode):
    """
    Tasks are supposed to be solved by players, the logic here is that if a task is solved (a)
    destination waypoint(s) will become available.
    """
    tid = UniqueIdProperty()
    description = StringProperty(required=True)
    media = StringProperty()
    destination = RelationshipTo('Waypoint', 'DESTINATION', cardinality=ZeroOrOne)


class TextTask(Task):
    solution = StringProperty()


class DateTask(Task):
    solution = DateProperty()


class ChoiceTask(Task):
    choices = ArrayProperty(StringProperty())
    solution = IntegerProperty()


class MultipleChoiceTask(ChoiceTask):
    """
    These are difficult, because of the multitude of possibilities
    for example:
        there are 4 choices, any different combination gives a different destination
        a, b, c, d -> (a,b),(a,c),(a,b,c),etc.
        in order to input this, each solution should point to the waypoint id associated with it
        (a,b):1,(a,b,c):2,(c,d):1
        so each array entry consists of (combination):id
    """
    solutions = ArrayProperty(StringProperty())
    destination = RelationshipTo('Waypoint', 'DESTINATION')


class UploadTask(Task):
    checksum = StringProperty()
