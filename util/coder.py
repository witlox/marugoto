#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json

from json import JSONEncoder, JSONDecoder
from time import strptime
from uuid import UUID

import networkx as nx

from model.dialog import Speech, Mail
from model.game import Waypoint, Level
from model.instance import GameInstance
from model.player import PlayerState, NonPlayableCharacterState
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
                'items': [json.dumps(i) for i in o.items] if o.items else None,
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
                'items': [json.dumps(i) for i in o.items] if o.items else None,
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
                'items': [json.dumps(i) for i in o.items] if o.items else None,
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
                'items': [json.dumps(i) for i in o.items] if o.items else None,
                'content': o.content
            }
        if isinstance(o, UUID):
            return o.hex
        if isinstance(o, GameInstance):
            return {
                '_type': 'GameInstance',
                '_key': o.id.hex,
                'name': o.name,
                'game': o.game.title,
                'game_master': o.game_master.id.hex,
                'created_at': o.created_at.strftime('%Y-%m-%d %H-%M-%S-%f'),
                'starts_at': o.starts_at.strftime('%Y-%m-%d %H-%M-%S-%f'),
                'ends_at': o.ends_at.strftime('%Y-%m-%d %H-%M-%S-%f'),
                'players': [json.dumps(p, cls=MarugotoEncoder) for p in o.player_states] if o.player_states else None,
                'npcs': [json.dumps(n, cls=MarugotoEncoder) for n in o.npc_states] if o.npc_states else None
            }
        if isinstance(o, PlayerState):
            dialogs = {}
            for npc, interactions in o.dialogs:
                dialogs[f'{npc.first_name} {npc.last_name}'] = [json.dumps(i, cls=MarugotoEncoder) for i in interactions]
            inventory = {}
            for stamp, kvs in o.inventory.items():
                inventory[stamp.strftime('%Y-%m-%d %H-%M-%S-%f')] = [{
                    'key': val[0].id.hex,
                    'value': json.dumps(val[1])
                } for val in kvs]
            return {
                '_type': 'PlayerState',
                '_key': f'{o.player.email}-{o.game_instance.id.hex}',
                'player': o.player.id.hex,
                'game': o.game_instance.id.hex,
                'first': o.first_name,
                'last': o.last_name,
                'path': [json.dumps(w, cls=MarugotoEncoder) for w in o.path],
                'dialogs': dialogs,
                'inventory': inventory,
            }
        if isinstance(o, NonPlayableCharacterState):
            paths = {}
            for player, interactions in o.paths.items():
                paths[json.dumps(player, cls=MarugotoEncoder)] = [json.dumps(i, cls=MarugotoEncoder) for i in interactions]
            return {
                '_type': 'NonPlayableCharacterState',
                '_key': f'{o.first_name} {o.last_name}',
                'game': o.game_instance.id.hex,
                'first': o.first_name,
                'last': o.last_name,
                'dialog': o.dialog.id.hex,
                'salutation': o.salutation,
                'mail': o.mail,
                'image': base64.encodebytes(o.image) if o.image else None,
                'paths': paths
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
        if obj['_type'] == 'GameInstance':
            game_instance = GameInstance(obj['game'],
                                         obj['name'],
                                         obj['game_master'],
                                         strptime(obj['starts_at'], '%Y-%m-%d %H-%M-%S-%f'),
                                         strptime(obj['ends_at'], '%Y-%m-%d %H-%M-%S-%f'))
            game_instance.created_at = strptime(obj['created_at'], '%Y-%m-%d %H-%M-%S-%f')
            game_instance.id = UUID(obj['_key'])
            if obj['players']:
                for player in obj['players']:
                    game_instance.player_states.append(json.loads(player, cls=MarugotoDecoder))
            if obj['npcs']:
                for npc in obj['npcs']:
                    game_instance.npc_states.append(json.loads(npc, cls=MarugotoDecoder))
            return game_instance
        if obj['_type'] == 'PlayerState':
            player = PlayerState(obj['player'], obj['first_name'], obj['last_name'], None)
            for waypoint in obj['path']:
                player.path.append(json.loads(waypoint, cls=MarugotoDecoder))
            for npc, interactions in obj['dialogs'].items():
                player.dialogs[npc] = [json.loads(i, cls=MarugotoDecoder) for i in interactions]
            for stamp, kvs in obj['inventory']:
                player.inventory[strptime(stamp, '%Y-%m-%d %H-%M-%S-%f')] = [(k['key'], json.loads(v['value'])) for k, v in kvs]
            return player
        if obj['_type'] == 'NonPlayableCharacterState':
            npc = NonPlayableCharacterState(obj['first_name'],
                                            obj['last_name'],
                                            None,
                                            obj['dialog'],
                                            obj['salutation'],
                                            obj['mail'],
                                            base64.decodebytes(obj['image']) if obj['image'] else None)

            for player, interactions in obj['paths'].items():
                npc.paths[json.loads(player, cls=MarugotoDecoder)] = [json.loads(i, cls=MarugotoDecoder) for i in interactions]
            return npc
        return obj
