#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from neomodel import StructuredNode, StringProperty, IntegerProperty, ArrayProperty, DateProperty, DateTimeProperty, \
    RelationshipTo, UniqueIdProperty


class Input(StructuredNode):
    iid = UniqueIdProperty()
    at = DateTimeProperty(default_now=True)
    waypoint = RelationshipTo('Waypoint', 'WAYPOINT')


class TextInput(Input):
    text = StringProperty()


class DateInput(Input):
    date = DateProperty()


class ChoiceInput(Input):
    choice = IntegerProperty()


class MultipleChoiceInput(Input):
    choices = ArrayProperty(IntegerProperty())


class UploadInput(Input):
    checksum = StringProperty()
