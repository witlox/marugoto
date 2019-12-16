#!/usr/bin/env python
# -*- coding: utf-8 -*-#
import json
import os

from arango import ArangoClient
from connexion import NoContent
from flask import session

from database.game import get_all_games, read, create, GameStateException, delete
from util.coder import MarugotoEncoder
from util.converter import convert_api_game, ConverterException


def all_games():
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    result = []
    for name in get_all_games(db):
        result.append(json.dumps(read(db, name), cls=MarugotoEncoder))
    return result, 200


def add_game(game):
    title = game['title']
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    try:
        game = convert_api_game(game)
        create(db, game, session['uid'])
    except ConverterException as e:
        return f"error while converting game {title}: {e}", 500
    except GameStateException as e:
        return f"error while saving game {title}: {e}", 500
    return NoContent, 200


def remove_game(title):
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    db = client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    try:
        game = read(db, title)
        delete(db, game, session['uid'])
    except GameStateException as e:
        return f"error while deleting game {title}: {e}", 500
    return NoContent, 200
