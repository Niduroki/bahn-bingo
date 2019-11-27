import os
import tempfile
from itertools import product
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta

from main import app, db


@pytest.fixture
def client():
    db_fd, db_file = tempfile.mkstemp()
    app.config['DATABASE'] = "sqlite://" + db_file
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.get_session()  # Initialize db
        yield client

    os.close(db_fd)
    os.unlink(db_file)


# TODO Zeitzonen Krams sowohl mit Sommer als auch Winterzeit testen (also wahrscheinlich freezegun aus Projekt Play)
def test_timezone_submit(client):
    #TODO
    # feld erstellen, prüfen ob tz richtig angezeigt wird
    # auch prüfen ob es richtig gespeichert wird - in der Datenbank ist CEST, also: Zeit speichern, Zeit lesen. gelesene Zeit muss gleich gespeicherte Zeit sein
    # feld kreuzen, neu laden, prüfen ob tz bei den feldern richtig ist
    pass


def test_cheater_prevention(client):
    """ Check whether fields finished within 2 hours are detected as cheaters """

    # Create a field
    rv = client.post('/', data=dict(player_name="cheater"))
    game_link = rv.location[-11:-1]
    session = db.get_session()
    game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
    rv = client.get(f'/{game_link}/')
    assert b'Spieler: cheater' in rv.data
    # Tick five fields right now
    for x, y in product((1, 1, 1, 1), (1, 2, 3, 4)):
        rv = client.post(f'/{game_link}/submit/{x}/{y}/')
        assert {'data': 'success', 'x': x, 'y': y} == rv.get_json()
    rv = client.post(f'/{game_link}/submit/1/5/')
    assert {'data': 'cheater'} == rv.get_json()
    # Check if field has been deleted
    assert 0 == session.query(db.BingoField).filter(db.BingoField.id == game_pk).count()
    assert 0 == session.query(db.BingoSquares).filter(db.BingoSquares.bingo_field_id == game_pk).count()

    # Tick five fields after 1:55 hours
    with freeze_time(datetime.now()) as frozen_time:
        rv = client.post('/', data=dict(player_name="cheater155"))
        game_link = rv.location[-11:-1]
        session = db.get_session()
        game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
        rv = client.get(f'/{game_link}/')
        assert b'Spieler: cheater155' in rv.data
        # Wait 1:55 hours
        frozen_time.tick(delta=timedelta(hours=1, minutes=55))
        # Tick five fields now
        for x, y in product((1, 1, 1, 1), (1, 2, 3, 4)):
            rv = client.post(f'/{game_link}/submit/{x}/{y}/')
            assert {'data': 'success', 'x': x, 'y': y} == rv.get_json()
        rv = client.post(f'/{game_link}/submit/1/5/')
        assert {'data': 'cheater'} == rv.get_json()
        # Check if field has been deleted
        assert 0 == session.query(db.BingoField).filter(db.BingoField.id == game_pk).count()
        assert 0 == session.query(db.BingoSquares).filter(db.BingoSquares.bingo_field_id == game_pk).count()

        # Tick four fields after 1:55 hours and fifth after 2:05 hours – Should pass
        with freeze_time(datetime.now()) as frozen_time:
            rv = client.post('/', data=dict(player_name="legit"))
            game_link = rv.location[-11:-1]
            session = db.get_session()
            game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
            rv = client.get(f'/{game_link}/')
            assert b'Spieler: legit' in rv.data
            # Wait 1:55 hours
            frozen_time.tick(delta=timedelta(hours=1, minutes=55))
            # Tick four fields now
            for x, y in product((1, 1, 1, 1), (1, 2, 3, 4)):
                rv = client.post(f'/{game_link}/submit/{x}/{y}/')
                assert {'data': 'success', 'x': x, 'y': y} == rv.get_json()
            # Wait 10 minutes
            frozen_time.tick(delta=timedelta(minutes=10))
            rv = client.post(f'/{game_link}/submit/1/5/')
            assert {'data': 'finished', 'score': (1000000/125)} == rv.get_json()
            # Check if field is finished
            game = session.query(db.BingoField).filter(db.BingoField.id == game_pk).one()
            assert game.score == 1000000 / 125
            assert game.finished


def test_bingo_scoring(client):
    #TODO
    # feld erstellen und 5 kreuze setzen nach 3 Stunden (Score mit Erwartung vergleichen
    # dito mit 5 Stunden, 24 Stunden, 48 Stunden, 96 Stunden, 300 Stunden, 700 Stunden (danach ist der Cookie abgelaufen)
    pass
