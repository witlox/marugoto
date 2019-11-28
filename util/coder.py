#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json

from json import JSONEncoder, JSONDecoder
from uuid import UUID

import networkx as nx

from model.dialog import Interaction
from model.game import Waypoint, Level
from model.task import Task


class MarugotoEncoder(JSONEncoder):
    """
    Our custom serializer for transferring our objects to the database and over the API
    """
    def default(self, o):
        if isinstance(o, Waypoint):
            return {
                '_type': 'Waypoint',
                '_key': o.id.hex,
                'id': o.id.hex,
                'title': o.title,
                'description': o.description,
                'time_limit': o.time_limit,
                'money_limit': o.money_limit,
                'timer_visible': o.timer_visible,
                'level': json.dumps(o.level, cls=MarugotoEncoder),
                'tasks': [json.dumps(t, cls=MarugotoEncoder) for t in o.tasks],
                'interactions': [json.dumps(i, cls=MarugotoEncoder) for i in o.interactions]
            }
        if isinstance(o, Level):
            icon = base64.encodebytes(o.icon) if o.icon else None
            return {
                '_type': 'Level',
                'title': o.title,
                'icon': icon
            }
        if isinstance(o, Task):
            media = json.dumps(base64.encodebytes(o.media)) if o.media else None
            return {
                '_type': 'Task',
                'id': o.id.hex,
                'destination': json.dumps(o.destination, cls=MarugotoEncoder),
                'description': o.description,
                'text': o.text,
                'solution': o.solution,
                'media': media,
                'ratio': o.ratio,
                'days': o.days,
                'offset': o.offset
            }
        if isinstance(o, Interaction):
            return {
                '_type': 'Interaction',
                'id': o.id.hex,
                'destination': json.dumps(o.destination, cls=MarugotoEncoder),
                'description': o.description,
                'money_limit': o.money_limit,
                'time_limit': o.time_limit,
                'waypoints': [json.dumps(w, cls=MarugotoEncoder) for w in o.waypoints],
                'task': json.dumps(o.task, cls=MarugotoEncoder)
            }
        return JSONEncoder.default(self, o)


class MarugotoDecoder(JSONDecoder):
    """
    Our custom deserializer for receiving our objects from the database and from the API
    """
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj):
        if '_type' not in obj:
            return obj
        if obj['_type'] == 'Waypoint':
            waypoint = Waypoint(nx.DiGraph(),
                                obj['title'],
                                obj['description'],
                                obj['time_limit'],
                                obj['money_limit'],
                                obj['timer_visible'],
                                json.loads(obj['level'], cls=MarugotoDecoder))
            waypoint.id = UUID(obj['id'])
            for t in obj['tasks']:
                waypoint.add_task(json.loads(t, cls=MarugotoDecoder))
            for i in obj['interactions']:
                waypoint.add_interaction(json.loads(i, cls=MarugotoDecoder))
            return waypoint
        if obj['_type'] == 'Level':
            icon = base64.decodebytes(obj['icon']) if obj['icon'] else None
            return Level(obj['title'], icon)
        if obj['_type'] == 'Task':
            media = base64.decodebytes(obj['media']) if obj['media'] else None
            task = Task(json.loads(obj['destination'], cls=MarugotoDecoder),
                        obj['description'],
                        obj['text'],
                        obj['solution'],
                        media,
                        obj['ratio'],
                        obj['days'],
                        obj['offset'])
            task.id = UUID(obj['id'])
            return task
        if obj['_type'] == 'Interaction':
            interaction = Interaction(nx.DiGraph(),
                                      obj['description'],
                                      obj['money_limit'],
                                      obj['time_limit'],
                                      json.loads(obj['task'], cls=MarugotoDecoder),
                                      json.loads(obj['destination'], cls=MarugotoDecoder))
            interaction.id = UUID(obj['id'])
            interaction.waypoints = json.loads(obj['waypoints'], cls=MarugotoDecoder)
            return interaction
        return obj
