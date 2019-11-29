import os
import tempfile
from itertools import product
import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta
from random import randint

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


def test_basic_functionality(client):
    """Sanity test to see if everything works as intended"""
    # Create a field
    with freeze_time(datetime.now()) as frozen_time:
        rv = client.post('/', data=dict(player_name="player"))
        game_link = rv.location[-11:-1]
        session = db.get_session()
        game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
        rv = client.get(f'/{game_link}/')
        assert b'Spieler: player' in rv.data
        # Wait 15 minutes
        frozen_time.tick(delta=timedelta(minutes=15))
        # Check middle
        rv = client.post(f'/{game_link}/submit/3/3/')
        assert {'data': 'success', 'x': 3, 'y': 3} == rv.get_json()
        # Check if it's submitted to the db
        square_time = session.query(db.BingoSquares.check_time).filter(
            db.BingoSquares.bingo_field_id == game_pk, db.BingoSquares.x_position == 3, db.BingoSquares.y_position == 3
        ).one()[0]
        assert square_time is not None
        # Wait 15 minutes
        frozen_time.tick(delta=timedelta(minutes=15))
        # Uncheck middle
        rv = client.post(f'/{game_link}/submit/3/3/undo/')
        assert {'data': 'success', 'x': 3, 'y': 3} == rv.get_json()
        # Check if it's submitted to the db
        square_time = session.query(db.BingoSquares.check_time).filter(
            db.BingoSquares.bingo_field_id == game_pk, db.BingoSquares.x_position == 3, db.BingoSquares.y_position == 3
        ).one()[0]
        assert square_time is None
        # Now randomly check a field every hour until we have a bingo
        bingo = False
        checked = []
        minutes_passed = 30
        while not bingo:
            frozen_time.tick(delta=timedelta(hours=1))
            minutes_passed += 60
            # Search for an unchecked field
            unchecked_field = False
            while not unchecked_field:
                x = randint(1, 5)
                y = randint(1, 5)
                if [x, y] not in checked:
                    unchecked_field = True
            checked.append([x, y])
            # Check the field
            rv = client.post(f'/{game_link}/submit/{x}/{y}/')
            json_data = rv.get_json()
            # Check if it's submitted to the db
            square_time = session.query(db.BingoSquares.check_time).filter(
                db.BingoSquares.bingo_field_id == game_pk, db.BingoSquares.x_position == x,
                db.BingoSquares.y_position == y
            ).one()[0]
            assert square_time is not None

            if json_data['data'] == "success":
                assert {'data': 'success', 'x': x, 'y': y} == json_data
            elif json_data['data'] == "finished":
                assert {'data': 'finished', 'score': int(1000000 / minutes_passed)} == json_data
                # Check if the field is finished and the score is saved in the db
                game = session.query(db.BingoField).filter(db.BingoField.id == game_pk).one()
                assert game.finished
                assert game.score == int(1000000 / minutes_passed)
                # Finish the while-loop
                bingo = True


def test_timezone_submit(client):
    # Test both DST time and non DST time
    for dst, tz_time in [[True, datetime(2019, 6, 15, 12)], [False, datetime(2019, 12, 15, 12)]]:  # This is UTC time
        with freeze_time(tz_time) as frozen_time:
            # Create a field
            rv = client.post('/', data=dict(player_name="player"))
            game_link = rv.location[-11:-1]
            session = db.get_session()
            game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
            rv = client.get(f'/{game_link}/')
            assert b'Spieler: player' in rv.data
            # Check if the right tz is displayed CEST in DST CET otherwise
            if dst:
                assert b'Start-Zeit: 15.06.19 14:00 Uhr' in rv.data
            else:
                assert b'Start-Zeit: 15.12.19 13:00 Uhr' in rv.data
            # Check if the right tz was saved CEST in DST CET otherwise
            db_time = session.query(db.BingoField.start_time).filter(db.BingoField.id == game_pk).one()[0]
            if dst:
                assert db_time == tz_time + timedelta(hours=2)
            else:
                assert db_time == tz_time + timedelta(hours=1)
            # Wait an hour
            frozen_time.tick(delta=timedelta(hours=1))
            # Check a square
            rv = client.post(f'/{game_link}/submit/3/3/')
            assert {'data': 'success', 'x': 3, 'y': 3} == rv.get_json()
            rv = client.get(f'/{game_link}/')
            # Check if the right tz is displayed with the checked square
            if dst:
                assert b'<p>Zeit: 15.06.19 15:00 Uhr</p>' in rv.data  # Bingo Squares's html looks like this
            else:
                assert b'<p>Zeit: 15.12.19 14:00 Uhr</p>' in rv.data
            # Check if the right tz is displayed in the db
            db_time = session.query(db.BingoSquares.check_time).filter(
                db.BingoSquares.bingo_field_id == game_pk, db.BingoSquares.x_position == 3,
                db.BingoSquares.y_position == 3
            ).one()[0]
            if dst:
                assert db_time == tz_time + timedelta(hours=3)
            else:
                assert db_time == tz_time + timedelta(hours=2)


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
    """ Test whether score matches our expectations"""
    # Check scores after 3, 5, 24, 48, 96, 300 and 700 hours (after that the cookie expired)
    for hours in [3, 5, 24, 48, 96, 300, 700]:
        with freeze_time(datetime.now()) as frozen_time:
            rv = client.post('/', data=dict(player_name=f"{hours}hour"))
            game_link = rv.location[-11:-1]
            session = db.get_session()
            game_pk = session.query(db.BingoField.id).filter(db.BingoField.link == game_link).one()[0]
            rv = client.get(f'/{game_link}/')
            assert f'Spieler: {hours}hour'.encode() in rv.data
            # Wait some hours
            frozen_time.tick(delta=timedelta(hours=hours))
            # Create a bingo
            for x, y in product((1, 1, 1, 1), (1, 2, 3, 4)):
                rv = client.post(f'/{game_link}/submit/{x}/{y}/')
                assert {'data': 'success', 'x': x, 'y': y} == rv.get_json()
            rv = client.post(f'/{game_link}/submit/1/5/')
            assert {'data': 'finished', 'score': int(1000000 / (60*hours))} == rv.get_json()
            # Check if field is finished and score matches our expectation
            game = session.query(db.BingoField).filter(db.BingoField.id == game_pk).one()
            assert game.score == int(1000000 / (60*hours))
            assert game.finished


def test_cron(client):
    """Test if /cron/ cleans up properly"""
    with freeze_time(datetime.now()) as frozen_time:
        rv = client.post('/', data=dict(player_name="dead"))
        dead_link = rv.location[-11:-1]
        session = db.get_session()
        dead_pk = session.query(db.BingoField.id).filter(db.BingoField.link == dead_link).one()[0]
        rv = client.get(f'/{dead_link}/')
        assert b'Spieler: dead' in rv.data
        rv = client.post('/', data=dict(player_name="cookie"))
        cookie_link = rv.location[-11:-1]
        session = db.get_session()
        rv = client.get(f'/{cookie_link}/')
        assert b'Spieler: cookie' in rv.data
        rv = client.post(f'/{cookie_link}/submit/3/3/')
        assert {'data': 'success', 'x': 3, 'y': 3} == rv.get_json()
        # Wait seven days
        frozen_time.tick(delta=timedelta(days=8))
        rv = client.get('/cron/')
        assert {'data': 'success', 'finished': [dead_link]} == rv.get_json()
        # Check if the dead game has been deleted
        assert 0 == session.query(db.BingoField).filter(db.BingoField.id == dead_pk).count()
        assert 0 == session.query(db.BingoSquares).filter(db.BingoSquares.bingo_field_id == dead_pk).count()
        # Check if the slow game is still there
        assert 1 == session.query(db.BingoField).filter(db.BingoField.link == cookie_link).count()
        # Wait some more days
        frozen_time.tick(delta=timedelta(days=90))
        rv = client.get('/cron/')
        assert {'data': 'success', 'finished': [cookie_link]} == rv.get_json()
        assert session.query(db.BingoField.finished).filter(db.BingoField.link == cookie_link).one()[0]
        assert session.query(db.BingoField.score).filter(db.BingoField.link == cookie_link).one()[0] is None
