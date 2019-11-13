#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from neomodel import StructuredNode, StringProperty, RelationshipTo, ArrayProperty, BooleanProperty, EmailProperty, \
    UniqueIdProperty

from db.game import Waypoint
from db.inputs import Input, TextInput


class Player(StructuredNode):
    wid = UniqueIdProperty()
    mail = EmailProperty(unique_index=True)
    password = StringProperty()


class PlayerState(StructuredNode):
    """
    Relationship between players and their game state
    Any player can have multiple states for a given game
    """
    first_name = StringProperty(required=True)
    last_name = StringProperty(required=True)
    GENDERS = {'F': 'Female', 'M': 'Male', 'O': 'Other'}
    gender = StringProperty(required=True, choices=GENDERS)
    player = RelationshipTo('Player', 'PLAYER')
    game = RelationshipTo('GameInstance', 'GAME')
    solutions = ArrayProperty(Input())
    notes = ArrayProperty(TextInput())
    path = ArrayProperty(Waypoint())
    finished = BooleanProperty()
