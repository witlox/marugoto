#!/usr/bin/env python
# -*- coding: utf-8 -*-#
import json

import networkx as nx

from arango.database import StandardDatabase

from model.game import Game
from util.coder import MarugotoEncoder


class GameStateException(Exception):
    pass


def create_game(db: StandardDatabase, game: Game):
    if db.has_graph(game.title):
        raise GameStateException(f'${game.title} already defined')
    if not nx.is_directed_acyclic_graph(game.graph):
        raise GameStateException(f'${game.title} is not acyclic')
    if not game.start_is_set():
        raise GameStateException(f'${game.title} has no starting point')
    dbg = db.create_graph(game.title)
    dbg.create_vertex_collection('waypoints')
    path = dbg.create_edge_definition(
        edge_collection='path',
        from_vertex_collections=['waypoints'],
        to_vertex_collections=['waypoints']
    )
    # add all nodes
    for node in set(game.start.all_path_nodes()):
        dbg.insert_vertex('waypoints', json.dumps(node, cls=MarugotoEncoder))

    dbg.create_vertex_collection('tasks')
    dbg.create_vertex_collection('interactions')
    # traverse the game graph

    identified = {}

    def walk(s, i):
        """
        Walk through the game path from a starting source
        :param s: starting waypoint for traversal
        :param i: dict containing identified steps
        """
        for successor in game.graph.successors(s):
            if s not in i.keys():
                i[s] = []
                print(s)
            if successor not in i[s]:
                print(f'{s} -> {successor}')
                path.insert({
                    '_key': f'{s.id.hex}-{successor.id.hex}',
                    '_from': f'waypoints/{s.id.hex}',
                    '_to': f'waypoints/{successor.id.hex}'
                })
                identified[s].append(successor)
                walk(successor, i)

    walk(game.start, identified)


def read_game(db: StandardDatabase, game: Game):
    if not db.has_graph(game.title):
        raise GameStateException(f'${game.title} does not exist')


def get_all_games(db: StandardDatabase, ):
    pass


def update_game(db: StandardDatabase, game: Game):
    if not db.has_graph(game.title):
        raise GameStateException(f'${game.title} does not exist')


def delete_game(db: StandardDatabase, game: Game):
    if not db.has_graph(game.title):
        raise GameStateException(f'${game.title} does not exist')
