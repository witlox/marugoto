#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import json

import pytest
import requests
from arango import ArangoClient

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from database.game import create, read, update, delete, get_all_games, get_all_dialogs
from model.dialog import Dialog, Mail, Speech
from model.game import Waypoint, Game
from model.player import NonPlayableCharacter
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
                  start  (path with dialog)
                  /   \
               w1 (m1) w2 (d1)
                  \   /
                   knot1
                 /  |  \
                w3  w4 w5  <- with task t1,t2,t3
                \   |
                  end <- task from dialog td1
    :return: game with described graph
    """
    #TODO, check interaction model in waypoint
    dialog = Dialog()
    dialog_start = Mail(dialog.graph, 'start sub', 'start body')
    m1 = Mail(dialog.graph, 'second sub', 'second body')
    td1 = Task(None, 'some task 1', 'some task', 'some solution')
    d1 = Speech(dialog.graph, 'content', task=td1)

    game = Game('test')
    start = Waypoint(game.graph, 'start')
    w1 = Waypoint(game.graph, 'w1')
    w2 = Waypoint(game.graph, 'w2')
    knot = Waypoint(game.graph, 'knot')
    w3 = Waypoint(game.graph, 'w3')
    t1 = Task(w3, 'some task 1', 'some task')
    w4 = Waypoint(game.graph, 'w4')
    t2 = Task(w4, 'some task 2', 'some task')
    w5 = Waypoint(game.graph, 'w5')
    t3 = Task(w5, 'some task 3', 'some task')
    end = Waypoint(game.graph, 'end')
    start.add_destination(w1)
    start.add_destination(w2)
    w1.add_destination(knot)
    w2.add_destination(knot)
    knot.add_task(t1)
    knot.add_task(t2)
    knot.add_task(t3)
    w3.add_destination(end)
    w4.add_destination(end)
    game.set_start(start)

    dialog_end = Speech(dialog.graph, 'next content', destination=end)
    dialog.set_start(dialog_start)
    dialog_start.add_follow_up(d1)
    dialog_start.add_follow_up(m1)
    dialog_start.waypoints.append(start)
    d1.add_follow_up(dialog_end, None)

    game.add_non_playable_character(NonPlayableCharacter('bob', 'test', dialog))

    return game


@pytest.fixture(scope='function')
def dialog():
    """
        start
        |   \
        m1  d1
            |  <- task required
            end
    :return: dialog with described graph
    """
    return dialog


def test_serialize_deserialize(game):
    js = json.dumps(game.start, cls=MarugotoEncoder)
    s = json.loads(js, cls=MarugotoDecoder)
    assert game.start == s
    wp = Waypoint(game.graph, 'test with task')
    task = Task(None, 'test task', 'some task')
    wp.add_task(task)
    jst = json.dumps(wp, cls=MarugotoEncoder)
    st = json.loads(jst, cls=MarugotoDecoder)
    assert wp == st
    assert task.id == st.tasks[0]


def test_game_crud(create_clean_db, game):
    create(create_clean_db, game)
    update(create_clean_db, game)
    assert game.title in get_all_games(create_clean_db)
    assert len(get_all_dialogs(create_clean_db)) > 0
    assert game.start == read(create_clean_db, game.title).start
    delete(create_clean_db, game)
