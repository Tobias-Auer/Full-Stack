import os
import sqlite3

import pytest

from main import app

app_directory = os.path.join(os.path.dirname(__file__), '..')
os.chdir(app_directory)



@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def get_player_names():
    conn = sqlite3.connect("./player_data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM cache')
    player_names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return player_names


# List of routes to be tested
routes_to_test = [
    '/',
    '/spieler'
]

@pytest.mark.parametrize('player', get_player_names())
def test_player_availability(client, player):
    path = f'/spieler?player={player}'
    response = client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize('route', routes_to_test)
def test_route_status_code(client, route):
    response = client.get(route)
    assert response.status_code == 200


if __name__ == '__main__':
    pytest.main()
