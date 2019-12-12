#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json
from datetime import datetime

from json import JSONEncoder, JSONDecoder
from time import strptime
from uuid import UUID

import networkx as nx

from model.dialog import Speech, Mail, Dialog
from model.game import Waypoint, Level, Game
from model.instance import GameInstance
from model.player import PlayerState, NonPlayableCharacterState, Player
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
                'budget_modification': o.budget_modification,
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
                'time_limit': o.time_limit,
                'money_limit': o.money_limit,
                'budget_modification': o.budget_modification,
                'ratio': o.ratio,
                'days': o.days,
                'offset': o.offset
            }
        if isinstance(o, Dialog):
            return {
                '_type': 'Dialog',
                '_key': o.id.hex,
                'start': o.start.id.hex
            }
        if isinstance(o, Mail):
            return {
                '_type': 'Mail',
                '_key': o.id.hex,
                'destination': o.destination.id.hex if o.destination else None,
                'description': o.description,
                'money_limit': o.money_limit,
                'time_limit': o.time_limit,
                'budget_modification': o.budget_modification,
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
                'budget_modification': o.budget_modification,
                'waypoints': [w.id.hex for w in o.waypoints],
                'task': o.task.id.hex if o.task else None,
                'items': [json.dumps(i) for i in o.items] if o.items else None,
                'content': o.content
            }
        if isinstance(o, Game):
            return {
                '_type': 'Game',
                'title': o.title,
                'image': base64.encodebytes(o.image) if o.image else None,
                'start': o.start.id.hex,
                'energy': o.energy
            }
        if isinstance(o, GameInstance):
            return {
                '_type': 'GameInstance',
                '_key': o.id.hex,
                'name': o.name,
                'game': json.dumps(o.game, cls=MarugotoEncoder),
                'game_master': json.dumps(o.game_master, cls=MarugotoEncoder),
                'created_at': o.created_at.strftime('%Y-%m-%d %H-%M-%S-%f'),
                'starts_at': o.starts_at.strftime('%Y-%m-%d %H-%M-%S-%f') if o.starts_at else None,
                'ends_at': o.ends_at.strftime('%Y-%m-%d %H-%M-%S-%f') if o.ends_at else None,
                'players': [json.dumps(p, cls=MarugotoEncoder) for p in o.player_states] if o.player_states else None,
                'npcs': [json.dumps(n, cls=MarugotoEncoder) for n in o.npc_states] if o.npc_states else None
            }
        if isinstance(o, Player):
            return {
                '_type': 'Player',
                '_key': o.id.hex,
                'mail': o.email,
                'password': o.password
            }
        if isinstance(o, PlayerState):
            dialogs = {}
            for npc, interactions in o.dialogs:
                dialogs[f'{npc.first_name} {npc.last_name}'] = [{'stamp': d.strftime('%Y-%m-%d %H-%M-%S-%f'),
                                                                 'interaction': json.dumps(i, cls=MarugotoEncoder),
                                                                 'response': r
                                                                 } for d, i, r in interactions]
            inventory = {}
            for stamp, kvs in o.inventory.items():
                inventory[stamp.strftime('%Y-%m-%d %H-%M-%S-%f')] = [{
                    'key': val[0].id.hex,
                    'value': json.dumps(val[1])
                } for val in kvs]
            return {
                '_type': 'PlayerState',
                '_key': f'{o.player.email}-{o.game_instance.id.hex}',
                'player': json.dumps(o.player, cls=MarugotoEncoder),
                'game': o.game_instance.id.hex,
                'first': o.first_name,
                'last': o.last_name,
                'energy': o.energy,
                'budget': o.budget,
                'path': [json.dumps(w, cls=MarugotoEncoder) for w in o.path],
                'dialogs': dialogs,
                'inventory': inventory,
            }
        if isinstance(o, NonPlayableCharacterState):
            paths = {}
            for player, interactions in o.paths.items():
                paths[json.dumps(player, cls=MarugotoEncoder)] = [{'stamp': d.strftime('%Y-%m-%d %H-%M-%S-%f'),
                                                                   'interaction': json.dumps(i, cls=MarugotoEncoder)
                                                                   } for d, i in interactions]
            return {
                '_type': 'NonPlayableCharacterState',
                '_key': f'{o.first_name} {o.last_name}',
                'game': o.game_instance.id.hex,
                'first': o.first_name,
                'last': o.last_name,
                'dialog': json.dumps(o.dialog, cls=MarugotoEncoder),
                'salutation': o.salutation,
                'mail': o.mail,
                'image': base64.encodebytes(o.image) if o.image else None,
                'paths': paths
            }
        if isinstance(o, UUID):
            return {'_type': 'UUID', 'value': o.hex}
        if isinstance(o, datetime):
            return {'_type': 'STAMP', 'value': o.strftime('%Y-%m-%d %H-%M-%S-%f')}
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
                                obj['budget_modification'],
                                [json.loads(i, cls=MarugotoDecoder) for i in obj['items']] if 'items' in obj and obj['items'] else None,
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
                        [json.loads(i, cls=MarugotoDecoder) for i in obj['items']] if 'items' in obj and obj['items'] else None,
                        obj['time_limit'],
                        obj['money_limit'],
                        obj['budget_modification'],
                        obj['ratio'],
                        obj['days'],
                        obj['offset'])
            task.id = UUID(obj['_key'])
            if obj['destination']:
                task.destination = UUID(obj['destination'])
            return task
        if obj['_type'] == 'Dialog':
            dialog = Dialog()
            dialog.start = UUID(obj['start'])
            dialog.id = UUID(obj['_key'])
            return dialog
        if obj['_type'] == 'Mail':
            mail = Mail(nx.DiGraph(),
                        obj['subject'],
                        obj['body'],
                        obj['description'],
                        obj['time_limit'],
                        obj['money_limit'],
                        obj['budget_modification'],
                        [json.loads(i, cls=MarugotoDecoder) for i in obj['items']] if 'items' in obj and obj['items'] else None)
            mail.id = UUID(obj['_key'])
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
                            obj['time_limit'],
                            obj['money_limit'],
                            obj['budget_modification'],
                            [json.loads(i, cls=MarugotoDecoder) for i in obj['items']] if 'items' in obj and obj['items'] else None)
            speech.id = UUID(obj['_key'])
            if obj['destination']:
                speech.destination = UUID(obj['destination'])
            if obj['task']:
                speech.task = UUID(obj['task'])
            for w in obj['waypoints']:
                speech.waypoints.append(UUID(w))
            return speech
        if obj['_type'] == 'Game':
            game = Game(obj['title'])
            game.image = base64.decodebytes(obj['image']) if obj['image'] else None
            game.energy = obj['energy']
            game.start = UUID(obj['start'])
            return game
        if obj['_type'] == 'GameInstance':
            game_instance = GameInstance(json.loads(obj['game'], cls=MarugotoDecoder),
                                         obj['name'],
                                         json.loads(obj['game_master'], cls=MarugotoDecoder),
                                         strptime(obj['starts_at'], '%Y-%m-%d %H-%M-%S-%f') if obj['starts_at'] else None,
                                         strptime(obj['ends_at'], '%Y-%m-%d %H-%M-%S-%f') if obj['ends_at'] else None)
            game_instance.created_at = strptime(obj['created_at'], '%Y-%m-%d %H-%M-%S-%f')
            game_instance.id = UUID(obj['_key'])
            if obj['players']:
                for player in obj['players']:
                    game_instance.player_states.append(json.loads(player, cls=MarugotoDecoder))
            if obj['npcs']:
                for npc in obj['npcs']:
                    game_instance.npc_states.append(json.loads(npc, cls=MarugotoDecoder))
            return game_instance
        if obj['_type'] == 'Player':
            player = Player(obj['mail'], obj['password'])
            player.id = UUID(obj['_key'])
            return player
        if obj['_type'] == 'PlayerState':
            player_state = PlayerState(json.loads(obj['player'], cls=MarugotoDecoder),
                                       obj['first'],
                                       obj['last'],
                                       None,
                                       obj['budget'])
            player_state.energy = obj['energy']
            for waypoint in obj['path']:
                player_state.path.append(json.loads(waypoint, cls=MarugotoDecoder))

            for npc, interactions in obj['dialogs'].items():
                player_state.dialogs[npc] = [(strptime(i['stamp'], '%Y-%m-%d %H-%M-%S-%f'),
                                              json.loads(i['interaction'], cls=MarugotoDecoder),
                                              i['response']) for i in interactions]
            for stamp, kvs in obj['inventory']:
                player_state.inventory[strptime(stamp, '%Y-%m-%d %H-%M-%S-%f')] = [(k['key'],
                                                                                    json.loads(v['value'])
                                                                                    ) for k, v in kvs]
            return player_state
        if obj['_type'] == 'NonPlayableCharacterState':
            npc = NonPlayableCharacterState(obj['first'],
                                            obj['last'],
                                            None,
                                            json.loads(obj['dialog'], cls=MarugotoDecoder),
                                            obj['salutation'],
                                            obj['mail'],
                                            base64.decodebytes(obj['image']) if obj['image'] else None)

            for player, interactions in obj['paths'].items():
                npc.paths[json.loads(player, cls=MarugotoDecoder)] = [(strptime(i['stamp'], '%Y-%m-%d %H-%M-%S-%f'),
                                                                       json.loads(i['interaction'], cls=MarugotoDecoder)
                                                                       ) for i in interactions]
            return npc
        if obj['_type'] == 'UUID':
            return UUID(obj['value'])
        if obj['_type'] == 'STAMP':
            return strptime(obj['value'], '%Y-%m-%d %H-%M-%S-%f')
        return obj
