#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import os
import logging
import re
from time import time

from arango import ArangoClient
from connexion import NoContent
from flask import session
from jose import jwt, ExpiredSignatureError

from database.player import authenticate, add_token, remove_token, validate, get_all_player_emails, create, delete
from model.player import PlayerStateException, Player

logger = logging.getLogger('api.auth')


def generate_token(identifier):
    """
    generate a JWT token
    :param identifier: name of user or service
    :return: JWT token
    """
    logger.debug(f'generate token request for {identifier}')
    timestamp = int(time())
    payload = {
        "iss": os.getenv('TOKEN_ISSUER'),
        "iat": int(timestamp),
        "exp": int(timestamp + int(os.getenv('TOKEN_LIFETIME', 3600))),
        "sub": str(identifier),
    }
    token = jwt.encode(payload, os.getenv('SECRET_KEY'), algorithm=os.getenv('TOKEN_ALGO'))
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    add_token(db, identifier, token)
    return token


def user_by_token(token, required_scopes=None):
    try:
        return validate_token(token)[0]
    except:
        return None


def validate_token(token):
    """
    validate if token is valid and not expired
    :param token: JWT token
    :return: nothing or dict(mail, uid), 500, 401 or 200
    """
    logger.debug(f'validate token request for {token}')
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    player = validate(db, token)
    if player:
        try:
            jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=[os.getenv('TOKEN_ALGO')])
        except ExpiredSignatureError:
            logger.info(f'token {token} expired for {player.email}')
            remove_token(db, player.email, token)
            return NoContent, 401
        return dict(sub=player.email, uid=player.id), 200
    else:
        logger.warning(f'unable to validate {token}')
        return NoContent, 500


def login(player):
    """
    login user or service
    :param player: dict containing mail and password
    :return: nothing or token, 500, 200 or 401
    """
    if 'mail' not in player or 'password' not in player:
        return 'not all parameters supplies', 500
    mail = player['mail']
    password = player['password']
    logger.debug(f'login request for {mail}')
    if 'username' in session:
        return f'You are already logged in {mail}', 500
    else:
        client = ArangoClient(hosts=os.getenv('DB_URI'))
        db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
        player = authenticate(db, mail, password, os.getenv('SECRET_KEY'))
        if player:
            token = generate_token(mail)
            session['username'] = mail
            session['uid'] = player.id
            session['token'] = token
            return token, 200
    return NoContent, 401


def logout():
    """
    logout user or service
    :return: 200
    """
    logger.debug('logout request')
    if 'username' in session:
        del(session['username'])
    if 'uid' in session:
        del(session['uid'])
    if 'token' in session:
        del(session['token'])
    return NoContent, 200


def register(player):
    """
    register new user
    :param player: dict containing mail and password
    :return: msg or token, 500 or 200
    """
    if 'mail' not in player or 'password' not in player:
        return f'not all parameters supplies', 500
    mail = player['mail']
    password = player['password']
    logger.debug(f'new user request for {mail}')
    if 'username' in session:
        return f'You are already logged in {mail}', 500
    else:
        client = ArangoClient(hosts=os.getenv('DB_URI'))
        db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
        try:
            if next(iter([e for e in get_all_player_emails(db) if e == mail])):
                logger.warning(f'player already registered under {mail}')
                return f'player already registered under {mail}', 500
        except PlayerStateException:
            logger.info('players collection not initialized')
        if os.getenv('PASSWORD_COMPLEXITY') == 'simple':
            if len(password) < 6:
                return f'password needs to be at least 6 characters', 422
        else:
            if len(password) < 8:
                return f'password needs to be at least 8 characters', 422
            if not re.search(r'\d', password):
                return f'password needs at least 1 digit', 422
            if not re.search(r'[A-Z]', password):
                return f'password needs at least 1 upper case character', 422
            if not re.search(r'[a-z]', password):
                return f'password needs at least 1 lower case character', 422
            if not re.search(r'\W', password):
                return f"password needs at least one special symbol", 422
        player = create(db, mail, password, os.getenv('SECRET_KEY'))
        session['username'] = mail
        session['uid'] = player.id
        token = generate_token(mail)
        session['token'] = token
        return token, 201


def remove():
    """
    remove an existing player
    :return: msg, code
    """
    if 'token' not in session:
        return f'cannot find token', 500
    p, code = validate_token(session['token'])
    if code != 200:
        return f'problem removing player', code
    try:
        client = ArangoClient(hosts=os.getenv('DB_URI'))
        db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
        player = Player(p['sub'], '')
        player.id = p['uid']
        logger.info(f"deleting player {p['sub']} ({p['uid']})")
        delete(db, player)
        return logout()
    except PlayerStateException as e:
        return f"error while deleting player {p['sub']}, {e}", 500

