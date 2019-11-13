#!/usr/bin/env python
# -*- coding: utf-8 -*-#

from neomodel import StructuredNode, StringProperty, DateProperty, RelationshipTo, RelationshipFrom, DateTimeProperty, \
    UniqueIdProperty


class GameInstance(StructuredNode):
    iid = UniqueIdProperty()
    created_at = DateTimeProperty(default_now=True)
    game = RelationshipTo('Game', 'GAME')


class SinglePlayerInstance(GameInstance):
    player_state = RelationshipTo('PlayerState', 'PLAYERSTATE')


class MultiplayerInstance(GameInstance):
    name = StringProperty(required=True)
    game_master = RelationshipTo('Player', 'MASTER')
    starts_at = DateTimeProperty(required=True)
    ends_at = DateProperty(required=True)
    player_states = RelationshipFrom('PlayerState', 'PLAYERSTATES')
