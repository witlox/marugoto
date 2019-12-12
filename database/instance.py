#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import json
import logging
from datetime import datetime
from uuid import UUID

from arango.database import StandardDatabase

from database.game import read as game_read
from database.player import read as player_read
from model.instance import GameInstance
from model.player import Player
from util.coder import MarugotoEncoder, MarugotoDecoder


logger = logging.getLogger('database.instance')


class InstanceStateException(Exception):
    pass


def save(db: StandardDatabase, instance: GameInstance):
    """
    save a game instance
    :param db: connection
    :param instance: game
    """
    logger.info(f'save called for {instance.id} ({instance.game.title})')
    if not db.has_collection('instances'):
        logger.info('creating collection instances')
        db.create_collection('instances')
    col = db.collection('instances')
    txn_db = db.begin_transaction(read=col.name, write=col.name)
    txn_col = txn_db.collection('instances')
    txn_col.insert(json.dumps(instance, cls=MarugotoEncoder))
    txn_db.commit_transaction()


def load(db: StandardDatabase, game_id: str) -> GameInstance:
    """
    load a game instance by id
    :param db: connection
    :param game_id: game instance id
    :return Game Instance
    """
    logger.info(f'load called for {game_id}')
    if not db.has_collection('instances'):
        logger.warning('no collections for instances')
        raise InstanceStateException('no collections for instances')
    col = db.collection('instances')
    db_game_instance = next(col.find({'_key': game_id}), None)
    if not db_game_instance:
        logger.warning(f'could not find game instance {game_id}')
        raise InstanceStateException(f'could not find game instance {game_id}')
    game_instance = json.loads(json.dumps(db_game_instance), cls=MarugotoDecoder)
    game_instance.game = game_read(db, game_instance.game.title)
    for player_state in game_instance.player_states:
        if not isinstance(player_state.player, Player):
            player_state.player = player_read(db, player_state.player)
        player_state.game_instance = game_instance
    for npc_state in game_instance.npc_states:
        npc_state.game_instance = game_instance
        if isinstance(npc_state.dialog.start, UUID):
            npc_state.dialog = next(iter([d for d in [n.dialog for n in game_instance.game.npcs] if d.id == npc_state.dialog.id]), None)
        if not npc_state.dialog:
            logger.warning(f'could not find dialog for NPC {npc_state.first_name} {npc_state.last_name} '
                           f'in {game_instance.game.title} ({game_instance.id})')
            raise InstanceStateException(f'could not find dialog for NPC {npc_state.first_name} {npc_state.last_name} '
                                         f'in {game_instance.game.title} ({game_instance.id})')
    return game_instance


def saves(db: StandardDatabase, player: Player) -> [(datetime, str, str, str)]:
    """
    get all saves for a player
    :param db: connection
    :param player: target
    :return list of (creation date, game instance name, game title, pseudonym)
    """
    logger.info(f'saves requested for player {player.email}')
    if not db.has_collection('instances'):
        logger.warning('no collections for instances')
        raise InstanceStateException('no collections for instances')
    col = db.collection('instances')
    result = []
    for db_game_instance in col.all():
        game_instance = json.loads(json.dumps(db_game_instance), cls=MarugotoDecoder)
        game_instance.game = game_read(db, game_instance.game.title)
        for player_state in game_instance.player_states:
            if player_state.player.id == player.id:
                result.append((game_instance.created_at,
                               game_instance.name,
                               game_instance.game.title,
                               f'{player_state.first_name} {player_state.last_name}'))
    return result


def hosts(db: StandardDatabase, player: Player) -> [(datetime, str, str)]:
    """
    list all games hosted by a player as game master
    :param db: connection
    :param player: game master
    :return: list of (creation date, game instance name, game title)
    """
    logger.info(f'hosts requested for player {player.email}')
    if not db.has_collection('instances'):
        logger.warning('no collections for instances')
        raise InstanceStateException('no collections for instances')
    col = db.collection('instances')
    result = []
    for db_game_instance in col.all():
        game_instance = json.loads(json.dumps(db_game_instance), cls=MarugotoDecoder)
        game_instance.game = game_read(db, game_instance.game.title)
        if game_instance.game_master and game_instance.game_master.id == player.id:
            result.append((game_instance.created_at, game_instance.name, game_instance.game.title))
    return result
