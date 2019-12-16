#!/usr/bin/env python
# -*- coding: utf-8 -*-#
import json
import os

import pytest
import requests
import schemathesis
from arango import ArangoClient
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from app import Server
from model.game import Game, Waypoint
from model.task import Task
from util.converter import generate_api_game

ROOT_URL = '/api/v1'
default_account = {'mail': 'test@test.com', 'password': 'SuperComplexPassword1!'}


pytest_plugins = ("docker_compose",)


load_dotenv()


@pytest.fixture(scope='function')
def wait_for_api(function_scoped_container_getter):
    """
    Wait for the http api from neo4j to become responsive after calling docker-compose
    """
    request_session = requests.Session()
    retries = Retry(total=15, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))
    service = function_scoped_container_getter.get("arangodb")
    print(service)
    assert request_session.get(os.getenv('DB_URI'))
    return request_session, os.getenv('DB_URI')


@pytest.fixture(scope='function')
def create_clean_db(wait_for_api):
    client = ArangoClient(hosts=os.getenv('DB_URI'))
    sys_db = client.db('_system', username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    if sys_db.has_database(os.getenv('DB_NAME')):
        sys_db.delete_database(os.getenv('DB_NAME'))
    sys_db.create_database(os.getenv('DB_NAME'))
    return client.db(os.getenv('DB_NAME'), username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))


@pytest.fixture(scope="session")
def client():
    s = Server()
    with s.connexion_app.app.test_client() as c:
        yield c


def test_create_user_and_login(wait_for_api, create_clean_db, client):
    lg = client.post(
        f"{ROOT_URL}/register", json=default_account
    )
    assert lg.status_code == 201
    token = json.loads(lg.data)
    lg = client.post(
        f"{ROOT_URL}/unregister", headers={'X-TOKEN': token}
    )
    assert lg.status_code == 200


def test_create_and_delete_game(wait_for_api, create_clean_db, client):
    # create our game
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    w2 = Waypoint(game.graph, 'w2', items=['some item'])
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    task = Task(w2, 'test description', 'test text', 'answer')
    w1.add_task(task)
    w2.add_destination(end)
    game.set_start(start)
    # create user
    lg = client.post(
        f"{ROOT_URL}/register", json=default_account
    )
    assert lg.status_code == 201
    token = json.loads(lg.data)
    # convert it to an API object
    game_data = generate_api_game(game)
    lg = client.post(
        f"{ROOT_URL}/games", json=game_data, headers={'X-TOKEN': token}
    )
    assert lg.status_code == 201
    lg = client.get(
        f"{ROOT_URL}/games"
    )
    assert lg.status_code == 200
    assert game.title in [g['title'] for g in lg.data]
