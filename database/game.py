#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import base64
import json
import logging
from uuid import UUID

import networkx as nx

from arango.database import StandardDatabase

from model.dialog import Dialog
from model.game import Game
from model.player import NonPlayableCharacter
from util.coder import MarugotoEncoder, MarugotoDecoder


logger = logging.getLogger('database.game')


class GameStateException(Exception):
    pass


def create(db: StandardDatabase, game: Game, creator=None):
    """
    save a game to the database
    :param db: connection
    :param game: target
    :param creator: creator of the game
    """
    logger.info(f'create called for {game.title}')
    if not db.has_collection('games'):
        logger.info(f'games collection does not exist, creating it.')
        db.create_collection('games')
    db_games = db.collection('games')
    if db_games.find({'key': game.title}):
        logger.warning(f'{game.title} already in metadata')
        raise GameStateException(f'{game.title} already in metadata')
    if db.has_graph(game.title):
        logger.warning(f'{game.title} already defined')
        raise GameStateException(f'{game.title} already defined')
    if not nx.is_directed_acyclic_graph(game.graph):
        logger.warning(f'{game.title} is not acyclic')
        raise GameStateException(f'{game.title} is not acyclic')
    if not game.start_is_set():
        logger.warning(f'{game.title} has no starting point')
        raise GameStateException(f'{game.title} has no starting point')
    db_game_graph = db.create_graph(f'game_{game.title}')
    if not db_game_graph.has_vertex_collection('waypoints'):
        logger.info(f'waypoints vertex collection does not exist, creating it.')
        db_game_graph.create_vertex_collection('waypoints')
    path = db_game_graph.create_edge_definition(
        edge_collection='path',
        from_vertex_collections=['waypoints'],
        to_vertex_collections=['waypoints']
    )
    # add all game nodes
    for waypoint_vertex in set(game.start.all_path_nodes()):
        logger.debug(f'inserting waypoint vertex {repr(waypoint_vertex)}')
        db_game_graph.insert_vertex('waypoints', json.dumps(waypoint_vertex, cls=MarugotoEncoder))

    # tasks as documents
    if not db.has_collection('tasks'):
        logger.info(f'tasks collection does not exist, creating it.')
        db.create_collection('tasks')
    tasks = db.collection('tasks')

    # dialogs metadata
    if not db.has_collection('dialogs'):
        logger.info(f'dialogs does not exist, creating it.')
        db.create_collection('dialogs')
    db_dialogs = db.collection('dialogs')

    # npc dialog metadata
    if not db.has_collection('npcs'):
        logger.info(f'npcs collection does not exist, creating it.')
        db.create_collection('npcs')
    db_npcs = db.collection('npcs')

    for npc in game.npcs:
        if db_npcs.find({'_key': f'{game.title}-{npc.first_name}-{npc.last_name}'}):
            logger.warning(f'dialog {game.title}-{npc.first_name}-{npc.last_name} already in metadata')
            raise GameStateException(f'dialog {game.title}-{npc.first_name}-{npc.last_name} already in metadata')
        logger.debug(f'inserting npc {game.title}-{npc.first_name}-{npc.last_name} with dialog {npc.dialog.id.hex}')
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
            logger.warning(f'dialog {npc.dialog.id} already in metadata')
            raise GameStateException(f'dialog {npc.dialog.id} already in metadata')
        if db.has_graph(f'dialog_{npc.dialog.id.hex}'):
            logger.warning(f'dialog {npc.dialog.id} already defined')
            raise GameStateException(f'dialog {npc.dialog.id} already defined')
        if not nx.is_directed_acyclic_graph(npc.dialog.graph):
            logger.warning(f'dialog {npc.dialog.id} is not acyclic')
            raise GameStateException(f'dialog {npc.dialog.id} is not acyclic')
        if not npc.dialog.start_is_set():
            logger.warning(f'dialog {npc.dialog.id} has no starting point')
            raise GameStateException(f'dialog {npc.dialog.id} has no starting point')
        db_dialog_graph = db.create_graph(f'dialog_{npc.dialog.id.hex}')
        if not db_dialog_graph.has_vertex_collection('interactions'):
            logger.debug(f'interaction vertex collection does not exist, creating it.')
            db_dialog_graph.create_vertex_collection('interactions')
        conversation = db_dialog_graph.create_edge_definition(
            edge_collection='conversation',
            from_vertex_collections=['interactions'],
            to_vertex_collections=['interactions']
        )
        # add all dialog nodes
        for interaction_vertex in set(npc.dialog.start.all_path_nodes()):
            logger.debug(f'inserting interaction vertex {repr(interaction_vertex)}')
            db_dialog_graph.insert_vertex('interactions', json.dumps(interaction_vertex, cls=MarugotoEncoder))

        dia_visited = {}

        def dialog_traversal(s, i):
            """
            Walk through the game path from a starting source
            :param s: starting waypoint for traversal
            :param i: dict containing identified steps
            """
            for successor in npc.dialog.graph.successors(s):
                logger.debug(f'successor {repr(successor)} for {repr(s)}')
                if s not in i.keys():
                    logger.debug(f'{repr(s)} is new, adding it')
                    i[s] = []
                if successor not in i[s]:
                    if successor.task:
                        logger.debug(f'{repr(successor)} has {repr(successor.task)}, adding to tasks')
                        task_dump = json.loads(json.dumps(successor.task, cls=MarugotoEncoder))
                        task_dump['_key'] = successor.task.id.hex
                        task_dump['for'] = successor.id.hex
                        if not tasks.find(task_dump):
                            tasks.insert(json.dumps(task_dump))
                    logger.debug(f'inserting interaction edge {repr(s)} to {repr(successor)}')
                    conversation.insert({
                        '_key': f'{s.id.hex}-{successor.id.hex}',
                        '_from': f'interactions/{s.id.hex}',
                        '_to': f'interactions/{successor.id.hex}'
                    })
                    dia_visited[s].append(successor)
                    dialog_traversal(successor, i)

        logger.debug(f'traversing dialog graph for {npc.first_name} {npc.last_name}')
        dialog_traversal(npc.dialog.start, dia_visited)
        logger.debug(f'inserting dialog {npc.dialog.id.hex}')
        db_dialogs.insert({
            '_key': npc.dialog.id.hex,
            'start': npc.dialog.start.id.hex
        })

    wp_visited = {}

    def game_traversal(s, i):
        """
        Walk through the game path from a starting source
        :param s: starting waypoint for traversal
        :param i: dict containing identified steps
        """
        for successor in game.graph.successors(s):
            logger.debug(f'successor {repr(successor)} for {repr(s)}')
            if s not in i.keys():
                logger.debug(f'{repr(s)} is new, adding it.')
                i[s] = []
            if successor not in i[s]:
                for task in successor.tasks:
                    logger.debug(f'{repr(successor)} has {repr(task)}, adding to tasks')
                    task_dump = json.loads(json.dumps(task, cls=MarugotoEncoder))
                    task_dump['_key'] = task.id.hex
                    task_dump['for'] = successor.id.hex
                    if not tasks.find(task_dump):
                        tasks.insert(json.dumps(task_dump))
                logger.debug(f'waypoint interaction edge {repr(s)} to {repr(successor)}')
                weight = game.graph.edges[s, successor]['weight'] if 'weight' in game.graph.edges[s, successor] and game.graph.edges[s, successor]['weight'] else None
                path.insert({
                    '_key': f'{s.id.hex}-{successor.id.hex}',
                    '_from': f'waypoints/{s.id.hex}',
                    '_to': f'waypoints/{successor.id.hex}',
                    'weight': weight
                })
                wp_visited[s].append(successor)
                game_traversal(successor, i)

    logger.debug(f'traversing game graph for {game.title}')
    game_traversal(game.start, wp_visited)
    logger.debug(f'inserting game {game.title}')
    db_games.insert({
        '_key': game.title,
        'start': game.start.id.hex,
        'image': base64.encodebytes(game.image) if game.image else None,
        'creator': creator
    })


def read(db: StandardDatabase, title: str) -> Game:
    """
    load an existing game back from the database
    :param db: connection
    :param title: game title
    :return: game object
    """
    logger.info(f'read called for {title}')
    npcs = []
    db_npcs = db.collection('npcs')
    db_dialogs = db.collection('dialogs')
    for db_npc in db_npcs.find({'game': f'game_{title}'}):
        logger.debug(f'reading back npc {db_npc["_key"]}')
        db_dialog = next(db_dialogs.find({'_key': db_npc['dialog']}), None)
        if not db_dialog:
            logger.warning(f"dialog {db_npc['dialog']} not in metadata")
            raise GameStateException(f"dialog {db_npc['dialog']} not in metadata")
        if not db.has_graph(f"dialog_{db_npc['dialog']}"):
            logger.warning(f"dialog {db_npc['dialog']} does not exist")
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
            logger.debug(f'got {repr(interaction)}')
            for task in db.collection('tasks'):
                if task['for'] == interaction.id.hex:
                    interaction.task = json.loads(json.dumps(task), cls=MarugotoDecoder)
                    logger.debug(f'got {repr(interaction.task)} for {repr(interaction)}')
            interactions.append(interaction)

        start_index = -1
        for e in path:
            if not e['edges']:
                start = next(iter([i for i in interactions if i.id == UUID(e['vertices'][0]['_key'])]), None)
                if start:
                    start_index = interactions.index(start)
                    logger.debug(f'setting start index to {start_index}')
                continue
            for edge in e['edges']:
                source = next(iter([i for i in interactions if i.id == UUID(edge['_from'][13:])]), None)
                if not source:
                    logger.warning(f"malformed source for dialog {db_npc['dialog']}")
                    raise GameStateException(f"malformed source for dialog {db_npc['dialog']}")
                idx = interactions.index(source)
                destination = next(iter([i for i in interactions if i.id == UUID(edge['_to'][13:])]), None)
                if not destination:
                    logger.warning(f"malformed destination for {repr(source)} in dialog {db_npc['dialog']}")
                    raise GameStateException(f"malformed destination for {repr(source)} in dialog {db_npc['dialog']}")
                logger.debug(f'adding follow up interaction {repr(destination)} to {repr(source)}')
                source.add_follow_up(destination)
                logger.debug(f'setting index for {repr(source)} to {idx}')
                interactions[idx] = source

        if start_index == -1:
            logger.warning(f"could not determine start for dialog {db_npc['dialog']}")
            raise GameStateException(f"could not determine start for dialog {db_npc['dialog']}")

        npc = NonPlayableCharacter(db_npc['first_name'], db_npc['last_name'], Dialog(interactions[start_index]))
        npc.salutation = db_npc['salutation']
        npc.mail = db_npc['mail']
        npc.image = base64.decodebytes(db_npc['image']) if db_npc['image'] else None
        logger.debug(f'adding {repr(npc)}')
        npcs.append(npc)

    games = db.collection('games')
    db_game = next(games.find({'_key': title}), None)
    if not db_game:
        logger.warning(f'game {title} not in metadata')
        raise GameStateException(f'game {title} not in metadata')
    if not db.has_graph(f'game_{title}'):
        logger.warning(f'game {title} does not exist')
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
        logger.debug(f'got {repr(waypoint)}')
        for task in db.collection('tasks'):
            if task['for'] == waypoint.id.hex:
                waypoint.tasks.remove(UUID(task['_key']))
                task = json.loads(json.dumps(task), cls=MarugotoDecoder)
                logger.debug(f'got {repr(task)} for {repr(waypoint)}')
                waypoint.tasks.append(task)
        if waypoint.interactions:
            for i in waypoint.interactions:
                if isinstance(i, UUID):
                    interaction = next(iter([ita for ita in [d.all_path_nodes() for d in [npc.dialog for npc in npcs]] if ita.id == i]), None)
                    if interaction:
                        logger.debug(f'adding {repr(interaction)} to {repr(waypoint)}')
                        waypoint.interactions.append(interaction)
                    else:
                        logger.warning(f'could not locate interaction {i}')
                        raise GameStateException(f'could not locate interaction {i}')
        waypoints.append(waypoint)

    # glue back the task destinations for waypoints
    for task in [ts for t in [w.tasks for w in waypoints if w.tasks] for ts in t]:
        if task.destination and isinstance(task.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == task.destination]), None)
            if not destination:
                logger.warning(f'could not find destination {task.destination} for task {task.id} in game {title}')
                raise GameStateException(f'could not find destination {task.destination} for task {task.id} in game {title}')
            logger.debug(f'adding {repr(destination)} to {repr(task)}')
            task.destination = destination
    # glue back interaction destinations for waypoints
    for interaction in [ias for ia in [w.interactions for w in waypoints if w.interactions] for ias in ia]:
        if interaction.destination and isinstance(interaction.destination, UUID):
            destination = next(iter([w for w in waypoints if w.id == interaction.destination]), None)
            if not destination:
                logger.warning(f'could not find destination {interaction.destination} for interaction {interaction.id} in game {title}')
                raise GameStateException(f'could not find destination {interaction.destination} for interaction {interaction.id} in game {title}')
            logger.debug(f'adding {repr(destination)} to {repr(interaction)}')
            interaction.destination = destination

    # glue back interaction and task destinations, and waypoints for dialogs
    for start in [d.start for d in [npc.dialog for npc in npcs]]:

        int_visited = {}

        def interaction_traversal(s, i, l):
            for successor in start.graph.successors(s):
                logger.debug(f'successor {repr(successor)} for {repr(s)}')
                if s not in i.keys():
                    logger.debug(f'{repr(s)} is new, adding it.')
                    i[s] = []
                if successor not in i[s]:
                    if s.destination and isinstance(s.destination, UUID):
                        destination = next(iter([w for w in l if w.id == s.destination]), None)
                        if not destination:
                            logger.warning(f'could not find destination {s.destination} for interaction {s.id} in game {title}')
                            raise GameStateException(f'could not find destination {s.destination} for interaction {s.id} in game {title}')
                        logger.debug(f'adding {repr(destination)} to {repr(s)}')
                        s.destination = destination
                    if s.task and s.task.destination and isinstance(s.task.destination, UUID):
                        destination = next(iter([w for w in l if w.id == s.task.destination]), None)
                        if not destination:
                            logger.warning(f'could not find destination {s.destination} for task {s.task.id} in interaction {s.id} in game {title}')
                            raise GameStateException(f'could not find destination {s.destination} for task {s.task.id} in interaction {s.id} in game {title}')
                        logger.debug(f'adding task destination {repr(destination)} to {repr(s.task)} for {repr(s)}')
                        s.task.destination = destination
                    if s.waypoints:
                        wps = []
                        for waypoint in s.waypoints:
                            if isinstance(waypoint, UUID):
                                destination = next(iter([w for w in l if w.id == waypoint]), None)
                                if not destination:
                                    logger.warning(f'could not find waypoint {waypoint} for interaction {interaction.id} in game {title}')
                                    raise GameStateException(f'could not find waypoint {waypoint} for interaction {interaction.id} in game {title}')
                                logger.debug(f'adding {repr(destination)}')
                                wps.append(destination)
                            else:
                                logger.debug(f'adding {repr(waypoint)}')
                                wps.append(waypoint)
                        s.waypoints = wps

                    int_visited[s].append(successor)
                    interaction_traversal(successor, i, l)

        logger.debug(f'starting interaction traversal to glue back waypoints')
        interaction_traversal(start, int_visited, waypoints)

    start_index = -1
    for e in path:
        if not e['edges']:
            start = next(iter([i for i in waypoints if i.id == UUID(e['vertices'][0]['_key'])]), None)
            if start:
                start_index = waypoints.index(start)
                logger.debug(f'settings start index to {start_index}')
            continue
        for edge in e['edges']:
            source = next(iter([i for i in waypoints if i.id == UUID(edge['_from'][10:])]), None)
            if not source:
                logger.warning(f'malformed source for game {title}')
                raise GameStateException(f'malformed source for game {title}')
            idx = waypoints.index(source)
            destination = next(iter([i for i in waypoints if i.id == UUID(edge['_to'][10:])]), None)
            if not destination:
                logger.warning(f'malformed destination for {source} in game {title}')
                raise GameStateException(f'malformed destination for {source} in game {title}')
            logger.debug(f'adding {repr(destination)} to {repr(source)}')
            if 'weight' in edge and edge['weight']:
                source.add_destination(destination, edge['weight'])
            else:
                source.add_destination(destination)
            logger.debug(f'setting index for {repr(source)} to {idx}')
            waypoints[idx] = source

    if start_index == -1:
        logger.warning(f'could not determine start for game {title}')
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


def delete(db: StandardDatabase, game: Game, requester=None):
    """
    delete all objects associated with a game
    :param db: connection
    :param game: target
    :param requester: player requesting the delete
    """
    logger.info(f'delete called for {game.title}')
    db_npcs = db.collection('npcs')
    db_dialogs = db.collection('dialogs')
    tasks = db.collection('tasks')
    games = db.collection('games')
    db_game = next(games.find({'_key': game.title}), None)
    if not db_game:
        logger.warning(f'game {game.title} not in metadata')
        raise GameStateException(f'game {game.title} not in metadata')
    if not db.has_graph(f'game_{game.title}'):
        logger.warning(f'game {game.title} not in metadata')
        raise GameStateException(f'game {game.title} does not exist')
    if db_game['creator'] and not db_game['creator'] == requester:
        raise GameStateException(f'cannot delete game {game.title}, you are not the owner')

    for db_npc in db_npcs.find({'game': f'game_{game.title}'}):
        db_dialog = next(db_dialogs.find({'_key': db_npc['dialog']}), None)
        if not db.has_graph(f"dialog_{db_npc['dialog']}"):
            logger.warning(f"dialog {db_npc['dialog']} does not exist")
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
    logger.info(f'update called for {game.title}')
    delete(db, game)
    create(db, game)


