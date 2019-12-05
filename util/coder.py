#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json

from json import JSONEncoder, JSONDecoder
from uuid import UUID

import networkx as nx

from model.dialog import Speech, Mail
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
                'title': o.title,
                'description': o.description,
                'time_limit': o.time_limit,
                'money_limit': o.money_limit,
                'timer_visible': o.timer_visible,
                'level': json.dumps(o.level, cls=MarugotoEncoder),
                'tasks': [t.id.hex for t in o.tasks],
                'items': [json.dumps(i, cls=MarugotoEncoder) for i in o.items] if o.items else None,
                'interactions': [i.id.hex for i in o.interactions]
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
                '_key': o.id.hex,
                'destination': o.destination.id.hex if o.destination else None,
                'description': o.description,
                'text': o.text,
                'solution': o.solution,
                'media': media,
                'items': [json.dumps(i, cls=MarugotoEncoder) for i in o.items] if o.items else None,
                'ratio': o.ratio,
                'days': o.days,
                'offset': o.offset
            }
        if isinstance(o, Mail):
            return {
                '_type': 'Mail',
                '_key': o.id.hex,
                'destination': o.destination.id.hex if o.destination else None,
                'description': o.description,
                'money_limit': o.money_limit,
                'time_limit': o.time_limit,
                'waypoints': [w.id.hex for w in o.waypoints],
                'task': o.task.id.hex if o.task else None,
                'items': [json.dumps(i, cls=MarugotoEncoder) for i in o.items] if o.items else None,
                'subject': o.subject,
                'body': o.body
            }
        if isinstance(o, Speech):
            return {
                '_type': 'Speech',
                '_key': o.id.hex,
                'destination': o.destination.id.hex if o.destination else None,
                'description': o.description,
                'money_limit': o.money_limit,
                'time_limit': o.time_limit,
                'waypoints': [w.id.hex for w in o.waypoints],
                'task': o.task.id.hex if o.task else None,
                'items': [json.dumps(i, cls=MarugotoEncoder) for i in o.items] if o.items else None,
                'content': o.content
            }
        if isinstance(o, UUID):
            return o.hex
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
            waypoint.id = UUID(obj['_key'])
            if 'items' in obj and obj['items']:
                for i in obj['items']:
                    waypoint.items.append(json.loads(i, cls=MarugotoDecoder))
            for t in obj['tasks']:
                waypoint.tasks.append(UUID(t))
            for i in obj['interactions']:
                waypoint.interactions.append(UUID(i))
            return waypoint
        if obj['_type'] == 'Level':
            icon = base64.decodebytes(obj['icon']) if obj['icon'] else None
            return Level(obj['title'], icon)
        if obj['_type'] == 'Task':
            media = base64.decodebytes(obj['media']) if obj['media'] else None
            task = Task(None,
                        obj['description'],
                        obj['text'],
                        obj['solution'],
                        media,
                        obj['ratio'],
                        obj['days'],
                        obj['offset'])
            task.id = UUID(obj['_key'])
            if 'items' in obj and obj['items']:
                for i in obj['items']:
                    task.items.append(json.loads(i, cls=MarugotoDecoder))
            if obj['destination']:
                task.destination = UUID(obj['destination'])
            return task
        if obj['_type'] == 'Mail':
            mail = Mail(nx.DiGraph(),
                        obj['subject'],
                        obj['body'],
                        obj['description'],
                        obj['money_limit'],
                        obj['time_limit'])
            mail.id = UUID(obj['_key'])
            if 'items' in obj and obj['items']:
                for i in obj['items']:
                    mail.items.append(json.loads(i, cls=MarugotoDecoder))
            if obj['destination']:
                mail.destination = UUID(obj['destination'])
            if obj['task']:
                mail.task = UUID(obj['task'])
            for w in obj['waypoints']:
                mail.waypoints.append(UUID(w))
            return mail
        if obj['_type'] == 'Speech':
            speech = Speech(nx.DiGraph(),
                            obj['content'],
                            obj['description'],
                            obj['money_limit'],
                            obj['time_limit'])
            speech.id = UUID(obj['_key'])
            if 'items' in obj and obj['items']:
                for i in obj['items']:
                    speech.items.append(json.loads(i, cls=MarugotoDecoder))
            if obj['destination']:
                speech.destination = UUID(obj['destination'])
            if obj['task']:
                speech.task = UUID(obj['task'])
            for w in obj['waypoints']:
                speech.waypoints.append(UUID(w))
            return speech
        return obj
