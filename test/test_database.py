#!/usr/bin/env python
# -*- coding: utf-8 -*-#
import json

import pytest
import requests
from arango import ArangoClient

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from database.game import create_game
from model.game import Game, Waypoint
from model.task import Task
from util.coder import MarugotoEncoder, MarugotoDecoder

pytest_plugins = ("docker_compose",)


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
    assert request_session.get('http://localhost:8529')
    return request_session, 'http://localhost:8529'


@pytest.fixture(scope='function')
def create_clean_db(wait_for_api):
    client = ArangoClient(hosts='http://localhost:8529')
    sys_db = client.db('_system', username='root', password='passwd')
    if sys_db.has_database('test'):
        sys_db.delete_database('test')
    sys_db.create_database('test')
    return client.db('test', username='root', password='passwd')


@pytest.fixture(scope='function')
def game():
    """
                  start
                  /   \
                 w1   w2
                  \   /
                   knot
                 /  |  \
                w3  w4 w5  <- with input
                \   |
                  end
    :return: game with described graph
    """
    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    w2 = Waypoint(game.graph, 'w2')
    knot = Waypoint(game.graph, 'knot')
    task = Task('some input', 'some answer')
    w3 = Waypoint(game.graph, 'w3')
    w4 = Waypoint(game.graph, 'w4')
    w5 = Waypoint(game.graph, 'w5')
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    start.add_destination(w2)
    w1.add_destination(knot)
    w2.add_destination(knot)
    knot.add_destination(w3, task)
    knot.add_destination(w4, task)
    knot.add_destination(w5, task)
    w3.add_destination(end)
    w4.add_destination(end)
    game.set_start(start)
    return game


def test_serialize_deserialize(game):
    js = json.dumps(game.start, cls=MarugotoEncoder)
    s = json.loads(js, cls=MarugotoDecoder)
    assert game.start == s
    task = Task('test task', 'some task')
    wp = Waypoint(game.graph, 'test with task')
    wp.add_destination(game.start, task)
    jst = json.dumps(wp, cls=MarugotoEncoder)
    st = json.loads(jst, cls=MarugotoDecoder)
    assert wp == st
    assert task.description == st.tasks[game.start].description


def test_create_read_database(create_clean_db, game):
    create_game(create_clean_db, game)