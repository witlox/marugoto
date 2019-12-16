#!/usr/bin/env python
# -*- coding: utf-8 -*-#
import base64
import json
import logging
from uuid import UUID

from model.dialog import Mail, Dialog
from model.game import Game
from util.coder import MarugotoEncoder, MarugotoDecoder

logger = logging.getLogger('util.converter')


class ConverterException(Exception):
    pass


def convert_api_game(game) -> Game:
    title = game['title']
    logger.debug(f"converting api game {title}")
    logger.debug('constructing tasks')
    tasks = [json.loads(t, cls=MarugotoDecoder) for t in game['tasks']]
    logger.debug('constructing waypoints')
    waypoints = [json.loads(w, cls=MarugotoDecoder) for w in game['waypoints']]

    logger.debug('constructing dialogs')
    dialogs = []
    all_interactions = []
    for d in game['dialogs']:
        dialog = Dialog()
        dialog.id = UUID(d['_key'])
        interactions = []

        def concretize(o):
            if o.task:
                task = next(iter([t for t in tasks if t.id == o.task]), None)
                if not task:
                    raise ConverterException(f"could not find task {o.task}")
                o.task = task
            dialog_waypoints = []
            for w in o.waypoints:
                waypoint = next(iter([wp for wp in waypoints if wp.id == w]))
                if not waypoint:
                    raise ConverterException(f"could not find waypoint {w}")
                dialog_waypoints.append(waypoint)
            o.waypoints = dialog_waypoints
            o.graph = dialog.graph
            interactions.append(o)

        for m in d['mails']:
            mail = json.loads(m, cls=MarugotoDecoder)
            concretize(mail)
        for s in d['speeches']:
            speech = json.loads(s, cls=MarugotoDecoder)
            concretize(speech)

        for vertex in d['graph'].items():
            f, t = vertex
            interaction_from = next(iter([i for i in interactions if i.id == UUID(f)]), None)
            interaction_to = next(iter([i for i in interactions if i.id == UUID(t)]), None)
            if not interaction_from or not interaction_to:
                raise ConverterException(f'could not find vertex interactions from {f} to {t}')
            interaction_from.add_follow_up(t)

        dialog.start = next(iter([i for i in interactions if i.id == UUID(d['start'])]), None)
        dialogs.append(dialog)
        all_interactions += interactions

    logger.debug('constructing NPCs')
    npcs = []
    for n in game['npcs']:
        npc = json.loads(n, cls=MarugotoDecoder)
        npc.dialog = next(iter([d for d in dialogs if d.id == npc.dialog.id]), None)
        npcs.append(npc)

    for waypoint in waypoints:
        # glue back tasks for waypoints
        waypoint_tasks = []
        for t in waypoint.tasks:
            task = next(iter([ta for ta in tasks if ta.id == t]), None)
            if not task:
                raise ConverterException(f'could not find task {t} for {title}')
            waypoint_tasks.append(task)
        waypoint.tasks = waypoint_tasks
        # glue back interactions for waypoints
        waypoint_interactions = []
        for i in waypoint.interactions:
            interaction = next(iter([it for it in all_interactions if it.id == i]), None)
            if not interaction:
                raise ConverterException(f'could not find interaction {i} for {title}')
            waypoint_interactions.append(interaction)
        waypoint.interactions = waypoint_interactions
    # glue back the task destinations for waypoints
    for task in [ts for t in [w.tasks for w in waypoints if w.tasks] for ts in t]:
        if task.destination and isinstance(task.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == task.destination]), None)
            if not destination:
                logger.warning(f'could not find destination {task.destination} for task {task.id} in game {title}')
                raise ConverterException(f'could not find destination {task.destination} for task {task.id} in game {title}')
            logger.debug(f'adding {repr(destination)} to {repr(task)}')
            task.destination = destination
    # glue back interaction destinations for waypoints
    for interaction in [ias for ia in [w.interactions for w in waypoints if w.interactions] for ias in ia]:
        if interaction.destination and isinstance(interaction.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == interaction.destination]), None)
            if not destination:
                logger.warning(f'could not find destination {interaction.destination} for interaction {interaction.id} in game {title}')
                raise ConverterException(f'could not find destination {interaction.destination} for interaction {interaction.id} in game {title}')
            logger.debug(f'adding {repr(destination)} to {repr(interaction)}')
            interaction.destination = destination

    result = json.loads(game, cls=MarugotoDecoder)
    result.start = next(iter([w for w in waypoints if w.id == result.start]), None)
    result.npcs = npcs
    for w in result.start:
        w.graph = result.graph
    return result


def generate_api_game(game: Game):
    logger.debug(f'converting {game.title}')
    return {
        'title': game.title,
        'image': base64.encodebytes(game.image) if game.image else None,
        'energy': game.energy,
        'graph': generate_vertices(game),
        'start': game.start.id.hex,
        'waypoints': [json.dumps(w, cls=MarugotoEncoder) for w in game.start.all_path_nodes()],
        'tasks': generate_tasks(game),
        'npcs': [json.dumps(npc, cls=MarugotoEncoder) for npc in game.npcs],
        'dialogs': generate_dialogs(game)
    }


def generate_dialogs(game: Game):
    result = []

    for npc in game.npcs:
        vertices = []
        npc_visited = {}

        dialog = json.dumps(npc.dialog, cls=MarugotoEncoder)
        if isinstance(npc.dialog.start, Mail):
            dialog['mails'] = [json.dumps(npc.dialog.start, cls=MarugotoEncoder)]
            dialog['speeches'] = []
        else:
            dialog['mails'] = []
            dialog['speeches'] = [json.dumps(npc.dialog.start, cls=MarugotoEncoder)]

        def dialog_traversal(s, i):
            for successor in npc.dialog.graph.successors(s):
                if s not in i.keys():
                    i[s] = []
                if successor not in i[s]:
                    if isinstance(successor, Mail):
                        dialog['mails'].append(json.dumps(successor, cls=MarugotoEncoder))
                    else:
                        dialog['speeched'].append(json.dumps(successor, cls=MarugotoEncoder))
                    vertices.append({
                        'from': s.id.hex,
                        'to': successor.id.hex
                    })
                    npc_visited[s].append(successor)
                    dialog_traversal(successor, i)

        dialog_traversal(npc.dialog.start, npc_visited)
        dialog['graph'] = vertices
        result.append(dialog)

    return result


def generate_tasks(game: Game):
    result = []

    wp_visited = {}

    def game_traversal(s, i):
        for successor in game.graph.successors(s):
            if s not in i.keys():
                i[s] = []
            if successor not in i[s]:
                for task in successor.tasks:
                    result.append(json.dumps(task, cls=MarugotoEncoder))
                wp_visited[s].append(successor)
                game_traversal(successor, i)

    game_traversal(game.start, wp_visited)

    for npc in game.npcs:
        npc_visited = {}

        def dialog_traversal(s, i):
            for successor in npc.dialog.graph.successors(s):
                if s not in i.keys():
                    i[s] = []
                if successor not in i[s]:
                    if successor.task:
                        result.append(json.dumps(successor.task, cls=MarugotoEncoder))
                    npc_visited[s].append(successor)
                    dialog_traversal(successor, i)

        dialog_traversal(npc.dialog.start, npc_visited)

    return result


def generate_vertices(game: Game):
    result = []
    wp_visited = {}

    def game_traversal(s, i):
        for successor in game.graph.successors(s):
            if s not in i.keys():
                i[s] = []
            if successor not in i[s]:
                weight = game.graph.edges[s, successor]['weight'] if 'weight' in game.graph.edges[s, successor] and game.graph.edges[s, successor]['weight'] else None
                result.append({
                    'from': s.id.hex,
                    'to': successor.id.hex,
                    'weight': weight
                })
                wp_visited[s].append(successor)
                game_traversal(successor, i)

    game_traversal(game.start, wp_visited)

    return result
