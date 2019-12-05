#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json
from uuid import UUID

import networkx as nx

from arango.database import StandardDatabase

from model.dialog import Dialog
from model.game import Game
from model.player import NonPlayableCharacter
from util.coder import MarugotoEncoder, MarugotoDecoder


class GameStateException(Exception):
    pass


def create(db: StandardDatabase, game: Game):
    """
    save a game to the database
    :param db: connection
    :param game: target
    """
    if not db.has_collection('games'):
        db.create_collection('games')
    db_games = db.collection('games')
    if db_games.find({'key': game.title}):
        raise GameStateException(f'{game.title} already in metadata')
    if db.has_graph(game.title):
        raise GameStateException(f'{game.title} already defined')
    if not nx.is_directed_acyclic_graph(game.graph):
        raise GameStateException(f'{game.title} is not acyclic')
    if not game.start_is_set():
        raise GameStateException(f'{game.title} has no starting point')
    db_game_graph = db.create_graph(f'game_{game.title}')
    if not db_game_graph.has_vertex_collection('waypoints'):
        db_game_graph.create_vertex_collection('waypoints')
    path = db_game_graph.create_edge_definition(
        edge_collection='path',
        from_vertex_collections=['waypoints'],
        to_vertex_collections=['waypoints']
    )
    # add all game nodes
    for waypoint_vertex in set(game.start.all_path_nodes()):
        db_game_graph.insert_vertex('waypoints', json.dumps(waypoint_vertex, cls=MarugotoEncoder))

    # tasks as documents
    if not db.has_collection('tasks'):
        db.create_collection('tasks')
    tasks = db.collection('tasks')

    # dialogs metadata
    if not db.has_collection('dialogs'):
        db.create_collection('dialogs')
    db_dialogs = db.collection('dialogs')

    # npc dialog metadata
    if not db.has_collection('npcs'):
        db.create_collection('npcs')
    db_npcs = db.collection('npcs')

    for npc in game.npcs:
        if db_npcs.find({'_key': f'{game.title}-{npc.first_name}-{npc.last_name}'}):
            raise GameStateException(f'dialog {game.title}-{npc.first_name}-{npc.last_name} already in metadata')
        db_npcs.insert({
            '_key': f'{game.title}-{npc.first_name}-{npc.last_name}',
            'game': f'game_{game.title}',
            'first_name': npc.first_name,
            'last_name': npc.last_name,
            'salutation': npc.salutation,
            'mail': npc.mail,
            'image': base64.encodebytes(npc.image) if npc.image else None,
            'dialog': npc.dialog.id.hex
        })

        if db_dialogs.find({'_key': npc.dialog.id.hex}):
            raise GameStateException(f'dialog {npc.dialog.id} already in metadata')
        if db.has_graph(f'dialog_{npc.dialog.id.hex}'):
            raise GameStateException(f'dialog {npc.dialog.id} already defined')
        if not nx.is_directed_acyclic_graph(npc.dialog.graph):
            raise GameStateException(f'dialog {npc.dialog.id} is not acyclic')
        if not npc.dialog.start_is_set():
            raise GameStateException(f'dialog {npc.dialog.id} has no starting point')
        db_dialog_graph = db.create_graph(f'dialog_{npc.dialog.id.hex}')
        if not db_dialog_graph.has_vertex_collection('interactions'):
            db_dialog_graph.create_vertex_collection('interactions')
        conversation = db_dialog_graph.create_edge_definition(
            edge_collection='conversation',
            from_vertex_collections=['interactions'],
            to_vertex_collections=['interactions']
        )
        # add all dialog nodes
        for interaction_vertex in set(npc.dialog.start.all_path_nodes()):
            db_dialog_graph.insert_vertex('interactions', json.dumps(interaction_vertex, cls=MarugotoEncoder))

        # traverse the dialog graph
        dia_visited = {}

        def dialog_traversal(s, i):
            """
            Walk through the game path from a starting source
            :param s: starting waypoint for traversal
            :param i: dict containing identified steps
            """
            for successor in npc.dialog.graph.successors(s):
                if s not in i.keys():
                    i[s] = []
                    if successor.task:
                        task_dump = json.loads(json.dumps(successor.task, cls=MarugotoEncoder))
                        task_dump['_key'] = successor.task.id.hex
                        task_dump['for'] = successor.id.hex
                        if not tasks.find(task_dump):
                            tasks.insert(json.dumps(task_dump))
                if successor not in i[s]:
                    conversation.insert({
                        '_key': f'{s.id.hex}-{successor.id.hex}',
                        '_from': f'interactions/{s.id.hex}',
                        '_to': f'interactions/{successor.id.hex}'
                    })
                    dia_visited[s].append(successor)
                    dialog_traversal(successor, i)

        dialog_traversal(npc.dialog.start, dia_visited)
        db_dialogs.insert({
            '_key': npc.dialog.id.hex,
            'start': npc.dialog.start.id.hex
        })

    # traverse the game graph

    wp_visited = {}

    def game_traversal(s, i):
        """
        Walk through the game path from a starting source
        :param s: starting waypoint for traversal
        :param i: dict containing identified steps
        """
        for successor in game.graph.successors(s):
            if s not in i.keys():
                i[s] = []
                for task in successor.tasks:
                    task_dump = json.loads(json.dumps(task, cls=MarugotoEncoder))
                    task_dump['_key'] = task.id.hex
                    task_dump['for'] = successor.id.hex
                    if not tasks.find(task_dump):
                        tasks.insert(json.dumps(task_dump))
            if successor not in i[s]:
                path.insert({
                    '_key': f'{s.id.hex}-{successor.id.hex}',
                    '_from': f'waypoints/{s.id.hex}',
                    '_to': f'waypoints/{successor.id.hex}'
                })
                wp_visited[s].append(successor)
                game_traversal(successor, i)

    game_traversal(game.start, wp_visited)
    db_games.insert({
        '_key': game.title,
        'start': game.start.id.hex,
        'image': base64.encodebytes(game.image) if game.image else None
    })


def read(db: StandardDatabase, title: str) -> Game:
    """
    load an existing game back from the database
    :param db: connection
    :param title: game title
    :return: game object
    """
    npcs = []
    db_npcs = db.collection('npcs')
    db_dialogs = db.collection('dialogs')
    for db_npc in db_npcs.find({'game': f'game_{title}'}):
        db_dialog = next(db_dialogs.find({'_key': db_npc['dialog']}), None)
        if not db_dialog:
            raise GameStateException(f"dialog {db_npc['dialog']} not in metadata")
        if not db.has_graph(f"dialog_{db_npc['dialog']}"):
            raise GameStateException(f"dialog {db_npc['dialog']} does not exist")

        vertices = []
        path = []
        for k, v in dict(db.graph(f"dialog_{db_npc['dialog']}").traverse(start_vertex=f"interactions/{db_dialog['start']}",
                                                                         direction='outbound',
                                                                         strategy='dfs',
                                                                         edge_uniqueness='global',
                                                                         vertex_uniqueness='global')).items():
            if k == 'vertices':
                for vertex in v:
                    vertices.append(vertex)
            elif k == 'paths':
                for edge in v:
                    path.append(edge)
        interactions = []
        for v in vertices:
            interaction = json.loads(json.dumps(v), cls=MarugotoDecoder)
            for task in db.collection('tasks'):
                if task['for'] == interaction.id.hex:
                    interaction.task = json.loads(json.dumps(task), cls=MarugotoDecoder)
            interactions.append(interaction)

        start_index = -1
        for e in path:
            if not e['edges']:
                start = next(iter([i for i in interactions if i.id == UUID(e['vertices'][0]['_key'])]), None)
                if start:
                    start_index = interactions.index(start)
                continue
            for edge in e['edges']:
                source = next(iter([i for i in interactions if i.id == UUID(edge['_from'][13:])]), None)
                if not source:
                    raise GameStateException(f"malformed source for dialog {db_npc['dialog']}")
                idx = interactions.index(source)
                destination = next(iter([i for i in interactions if i.id == UUID(edge['_to'][13:])]), None)
                if not destination:
                    raise GameStateException(f"malformed destination for {source} in dialog {db_npc['dialog']}")
                source.add_follow_up(destination)
                interactions[idx] = source

        if start_index == -1:
            raise GameStateException(f"could not determine start for dialog {db_npc['dialog']}")

        npc = NonPlayableCharacter(db_npc['first_name'], db_npc['last_name'], Dialog(interactions[start_index]))
        npc.salutation = db_npc['salutation']
        npc.mail = db_npc['mail']
        npc.image = base64.decodebytes(db_npc['image']) if db_npc['image'] else None
        npcs.append(npc)

    games = db.collection('games')
    db_game = next(games.find({'_key': title}), None)
    if not db_game:
        raise GameStateException(f'game {title} not in metadata')
    if not db.has_graph(f'game_{title}'):
        raise GameStateException(f'game {title} does not exist')
    vertices = []
    path = []
    for k, v in dict(db.graph(f'game_{title}').traverse(start_vertex=f"waypoints/{db_game['start']}",
                                                        direction='outbound',
                                                        strategy='dfs',
                                                        edge_uniqueness='global',
                                                        vertex_uniqueness='global')).items():
        if k == 'vertices':
            for vertex in v:
                vertices.append(vertex)
        elif k == 'paths':
            for edge in v:
                path.append(edge)
    waypoints = []
    for v in vertices:
        waypoint = json.loads(json.dumps(v), cls=MarugotoDecoder)
        for task in db.collection('tasks'):
            if task['for'] == waypoint.id.hex:
                waypoint.tasks.remove(UUID(task['_key']))
                waypoint.tasks.append(json.loads(json.dumps(task), cls=MarugotoDecoder))
        if waypoint.interactions:
            for i in waypoint.interactions:
                if isinstance(i, UUID):
                    interaction = next(iter([ita for ita in [d.all_path_nodes() for d in [npc.dialog for npc in npcs]] if ita.id == i]), None)
                    if interaction:
                        waypoint.interactions.append(interaction)
                    else:
                        raise GameStateException(f'could not locate interaction {i}')
        waypoints.append(waypoint)

    # glue back the task destinations for waypoints
    for task in [ts for t in [w.tasks for w in waypoints if w.tasks] for ts in t]:
        if task.destination and isinstance(task.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == task.destination]), None)
            if not destination:
                raise GameStateException(f'could not find destination {task.destination} for task {task.id} in game {title}')
            task.destination = destination
    # glue back interaction destinations for waypoints
    for interaction in [ias for ia in [w.interactions for w in waypoints if w.interactions] for ias in ia]:
        if interaction.destination and isinstance(interaction.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == interaction.destination]), None)
            if not destination:
                raise GameStateException(f'could not find destination {interaction.destination} for interaction {interaction.id} in game {title}')
            interaction.destination = destination

    # glue back interaction and task destinations, and waypoints for dialogs
    for start in [d.start for d in [npc.dialog for npc in npcs]]:

        int_visited = {}

        def interaction_traversal(s, i, l):
            for successor in start.graph.successors(s):
                if s not in i.keys():
                    i[s] = []
                if successor not in i[s]:
                    if s.destination and isinstance(s.destination, UUID):
                        destination = next(iter([w for w in l if w.id == s.destination]), None)
                        if not destination:
                            raise GameStateException(f'could not find destination {s.destination} for interaction {s.id} in game {title}')
                        s.destination = destination
                    if s.task and s.task.destination and isinstance(s.task.destination, UUID):
                        destination = next(iter([w for w in l if w.id == s.task.destination]), None)
                        if not destination:
                            raise GameStateException(f'could not find destination {s.destination} for task {s.task.id} in interaction {s.id} in game {title}')
                        s.task.destination = destination
                    if s.waypoints:
                        wps = []
                        for waypoint in s.waypoints:
                            if isinstance(waypoint, UUID):
                                destination = next(iter([w for w in l if w.id == waypoint]), None)
                                if not destination:
                                    raise GameStateException(f'could not find waypoint {waypoint} for interaction {interaction.id} in game {title}')
                                wps.append(destination)
                            else:
                                wps.append(waypoint)
                        s.waypoints = wps

                    int_visited[s].append(successor)
                    interaction_traversal(successor, i, l)

        interaction_traversal(start, int_visited, waypoints)

    start_index = -1
    for e in path:
        if not e['edges']:
            start = next(iter([i for i in waypoints if i.id == UUID(e['vertices'][0]['_key'])]), None)
            if start:
                start_index = waypoints.index(start)
            continue
        for edge in e['edges']:
            source = next(iter([i for i in waypoints if i.id == UUID(edge['_from'][10:])]), None)
            if not source:
                raise GameStateException(f'malformed source for game {title}')
            idx = waypoints.index(source)
            destination = next(iter([i for i in waypoints if i.id == UUID(edge['_to'][10:])]), None)
            if not destination:
                raise GameStateException(f'malformed destination for {source} in game {title}')
            source.add_destination(destination)
            waypoints[idx] = source

    if start_index == -1:
        raise GameStateException(f'could not determine start for game {title}')

    game = Game(title, base64.decodebytes(db_game['image']) if db_game['image'] else None, waypoints[start_index])
    game.npcs = npcs

    return game


def get_all_games(db: StandardDatabase) -> [str]:
    """
    get all game titles
    :param db: connection
    :return: list of all game names or empty list
    """
    return [d['_key'] for d in db.collection('games')]


def get_all_dialogs(db: StandardDatabase) -> [str]:
    """
    get all dialog ids
    :param db: connection
    :return: list of all dialogs in the system or empty list
    """
    return [d['_key'] for d in db.collection('dialogs') if '_key' in d]


def delete(db: StandardDatabase, game: Game):
    """
    delete all objects associated with a game
    :param db: connection
    :param game: target
    """
    db_npcs = db.collection('npcs')
    db_dialogs = db.collection('dialogs')
    tasks = db.collection('tasks')
    for db_npc in db_npcs.find({'game': f'game_{game.title}'}):
        db_dialog = next(db_dialogs.find({'_key': db_npc['dialog']}), None)
        if not db.has_graph(f"dialog_{db_npc['dialog']}"):
            raise GameStateException(f"dialog {db_npc['dialog']} does not exist")
        for k, v in dict(db.graph(f"dialog_{db_npc['dialog']}").traverse(start_vertex=f"interactions/{db_dialog['start']}",
                                                                         direction='outbound',
                                                                         strategy='dfs',
                                                                         edge_uniqueness='global',
                                                                         vertex_uniqueness='global')).items():
            if k == 'vertices':
                for interaction in v:
                    if 'task' in interaction and interaction['task']:
                        db_task = next(tasks.find({'_key': interaction['task']}))
                        if db_task:
                            db.delete_document(db_task)
        db.delete_document(db_dialog)
        db.delete_graph(f"dialog_{db_npc['dialog']}", drop_collections=True)
        db.delete_document(db_npc)
    games = db.collection('games')
    db_game = next(games.find({'_key': game.title}), None)
    if not db_game:
        raise GameStateException(f'game {game.title} not in metadata')
    if not db.has_graph(f'game_{game.title}'):
        raise GameStateException(f'game {game.title} does not exist')
    for node in nx.dfs_tree(game.graph):
        for task in node.tasks:
            db_task = next(tasks.find({'_key': task.id.hex}), None)
            if db_task:
                db.delete_document(db_task)
    db.delete_document(db_game)
    db.delete_graph(f'game_{game.title}', drop_collections=True)


def update(db: StandardDatabase, game: Game):
    """
    update an existing game (currenlty simply deletes and creates it again
    :param db: connection
    :param game: target
    """
    delete(db, game)
    create(db, game)


