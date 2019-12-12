#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import hashlib
import binascii
import logging
from uuid import UUID

from arango.database import StandardDatabase

from model.player import Player, PlayerStateException


logger = logging.getLogger('database.instance')


def hash_password(password, salt) -> str:
    """
    Hash a password for storing.
    :param password: target for encryption
    :param salt: encryption salt
    :return hashed password
    """
    salt = hashlib.sha256(salt.encode()).hexdigest().encode('ascii')
    password_hash = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000))
    return (salt + password_hash).decode('ascii')


def verify_password(stored_password, provided_password, salt):
    """
    Verify a stored password against one provided by user
    :param stored_password: password that was already hashed
    :param provided_password: clear text password to compare
    :return bool
    """
    salt = stored_password[:len(salt)]
    stored_password = stored_password[len(salt):]
    password_hash = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt.encode('ascii'), 100000))
    return password_hash == stored_password


def authenticate(db: StandardDatabase, email, password, salt):
    """
    validate player password
    :param db: connection
    :param email: mail
    :param password: plain text password
    :param salt: encryption salt
    :return: Player or None
    """
    if not db.has_collection('players'):
        logger.warning('cannot authenticate: no players defined')
        return None
    col = db.collection('players')
    db_player = next(col.find({'mail': email}), None)
    if not db_player:
        logger.warning(f'could not find player {email}')
        return None
    if verify_password(db_player['password'], hash_password(password, salt), salt):
        player = Player(db_player['mail'], '')
        player.id = UUID(db_player['_key'])
        player.password = db_player['password']
        return player


def add_token(db: StandardDatabase, email, token):
    """
    add a token to a player
    :param db: connection
    :param email: mail
    :param token: jwt token
    """
    if not db.has_collection('players'):
        logger.error('cannot add token if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': email}), None)
    if not db_player:
        logger.error(f'could not resolve player {email}')
        raise PlayerStateException(f'player {email} does not exist')
    db_player['tokens'].append(token)
    col.update(db_player)


def remove_token(db: StandardDatabase, email, token):
    """
    remove a token from player
    :param db: connection
    :param email: mail
    :param token: jwt token
    """
    if not db.has_collection('players'):
        logger.error('cannot remove token if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': email}), None)
    if not db_player:
        logger.error(f'could not resolve player {email}')
        raise PlayerStateException(f'player {email} does not exist')
    db_player['tokens'].remove(token)
    col.update(db_player)


def validate(db: StandardDatabase, token, email=None):
    """
    validate player token
    :param db: connection
    :param token: jwt token
    :param email: mail
    :return Player or None
    """
    if not db.has_collection('players'):
        logger.error('cannot validate token if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    if email:
        db_player = next(col.find({'mail': email}), None)
        if not db_player:
            logger.error(f'could not resolve player {email}')
            raise PlayerStateException(f'player {email} does not exist')
        if token in db_player['tokens']:
            player = Player(db_player['mail'], '')
            player.id = UUID(db_player['_key'])
            player.password = db_player['password']
            return player
    else:
        for db_player in col.all():
            if 'tokens' in db_player and token in db_player['tokens']:
                player = Player(db_player['mail'], '')
                player.id = UUID(db_player['_key'])
                player.password = db_player['password']
                return player
    return None


def create(db: StandardDatabase, email, password, salt) -> Player:
    """
    create a new player
    :param db: connection
    :param email: mail
    :param password: plain text password
    :param salt: encryption salt
    :return: Player
    """
    if not db.has_collection('players'):
        logger.info('creating collection players')
        db.create_collection('players')
    player = Player(email, hash_password(password, salt))
    col = db.collection('players')
    col.insert({'_key': player.id.hex, 'mail': player.email, 'password': player.password, 'tokens': []})
    return player


def read(db: StandardDatabase, player_id):
    """
    find existing player
    :param db: connection
    :param player_id: id
    :return: Player or None
    """
    if not db.has_collection('players'):
        logger.error('cannot resolve player if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'_key': player_id}), None)
    if not db_player:
        return None
    return Player(db_player['email'], db_player['password'])


def get_all_player_emails(db: StandardDatabase) -> [str]:
    """
    return all player email addresses
    :param db: connection
    :return: list of known mail addresses
    """
    if not db.has_collection('players'):
        logger.error('cannot resolve player if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    return [p['mail'] for p in col.all()]


def update(db: StandardDatabase, player: Player, salt, email: str = None, password: str = None, tokens: [str] = None) -> Player:
    """
    update attributes of existing player
    :param db: connection
    :param player: target
    :param salt: encryption salt
    :param email: new mail
    :param password: new password in plain text
    :param tokens: non-expired tokens for player
    :return: Player
    """
    if not db.has_collection('players'):
        logger.error('cannot resolve player if players do not exist')
        raise PlayerStateException('players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': player.email}), None)
    if not db_player:
        logger.error(f'cannot find player {player.email}')
        raise PlayerStateException(f'could not find player {player.email}')
    if email and password:
        player = Player(email, hash_password(password, salt))
    elif email:
        player = Player(email, db_player['password'])
    elif password:
        player = Player(db_player['mail'], hash_password(password, salt))
    else:
        player = Player(db_player['mail'], db_player['password'])
    player.id = UUID(db_player['_key'])
    col.update({'_key': player.id.hex, 'mail': player.email, 'password': player.password})
    return player


def delete(db: StandardDatabase, player: Player):
    """
    remove existing player
    :param db: connection
    :param player: target
    """
    if not db.has_collection('players'):
        logger.error('cannot remove player if players do not exist')
        raise PlayerStateException(f'players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': player.email}), None)
    if not db_player:
        logger.error(f'cannot find player {player.email}')
        raise PlayerStateException(f'could not find player {player.email}')
    col.delete(db_player)
