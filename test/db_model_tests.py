import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from neomodel import db, clear_neo4j_database, OUTGOING, Traversal

from db.game import Waypoint, Game, Start


pytest_plugins = ("docker_compose",)


@pytest.fixture(scope='function')
def wait_for_api(function_scoped_container_getter):
    """
    Wait for the http api from neo4j to become responsive after calling docker-compose
    """
    request_session = requests.Session()
    retries = Retry(total=15, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))
    service = function_scoped_container_getter.get("neo4j")
    print(service)
    assert request_session.get('http://localhost:7474')
    return request_session, 'http://localhost:7474'


def test_waypoint_traversal(wait_for_api):
    clear_neo4j_database(db)
    start = Start().save()
    w1 = Waypoint().save()
    w2 = Waypoint().save()
    finish = Waypoint().save()
    assert start.destination.connect(w1)
    assert start.destination.connect(w2)
    assert w1.destination.connect(finish)
    assert w2.destination.connect(finish)
    game = Game(title='test')
    game.save()
    game.start.connect(start)
    assert finish.is_finish()
    assert len(game.nodes.all()) == 1
    definition = dict(node_class=Waypoint, direction=OUTGOING, relation_type=None, model=None)
    assert len(Traversal(start, Waypoint.__label__, definition).all()) == 2
    assert len(Traversal(w2, Waypoint.__label__, definition).all()) == 1
