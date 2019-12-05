#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import hashlib
import binascii
from uuid import UUID

from arango.database import StandardDatabase

from model.player import Player, PlayerStateException


def hash_password(password, salt: bytes) -> str:
    """
    Hash a password for storing.
    :param password: target for encryption
    :param salt: encryption salt (60 bytes)
    :return hashed password
    """
    if len(salt) != 60:
        raise PlayerStateException(f'salt value not 60 bytes')
    salt = hashlib.sha256(salt).hexdigest().encode('ascii')
    password_hash = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000))
    return (salt + password_hash).decode('ascii')


def verify_password(stored_password, provided_password):
    """
    Verify a stored password against one provided by user
    :param stored_password: password that was already hashed
    :param provided_password: clear text password to compare
    :return bool
    """
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    password_hash = binascii.hexlify(hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt.encode('ascii'), 100000))
    return password_hash == stored_password


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
        db.create_collection('players')
    player = Player(email, hash_password(password, salt))
    col = db.collection('players')
    col.insert({'_key': player.id.hex, 'mail': player.email, 'password': player.password})
    return player


def read(db: StandardDatabase, player_id):
    """
    find existing player
    :param db: connection
    :param email: mail
    :return: Player or None
    """
    if not db.has_collection('players'):
        raise PlayerStateException(f'players collection does not exist')
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
        raise PlayerStateException(f'players collection does not exist')
    col = db.collection('players')
    return [p['mail'] for p in col.all()]

def update(db: StandardDatabase, player: Player, salt, email: str = None, password: str = None) -> Player:
    """
    update attributes of existing player
    :param db: connection
    :param player: target
    :param salt: encryption salt
    :param email: new mail
    :param password: new password in plain text
    :return: Player
    """
    if not db.has_collection('players'):
        raise PlayerStateException(f'players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': player.email}), None)
    if not db_player:
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
        raise PlayerStateException(f'players collection does not exist')
    col = db.collection('players')
    db_player = next(col.find({'mail': player.email}), None)
    if not db_player:
        raise PlayerStateException(f'could not find player {player.email}')
    col.delete(db_player)
