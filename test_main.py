import pytest
from main import app


@pytest.fixture
def client():
    app.config['DATABASE'] = "sqlite://"
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# TODO Zeitzonen Krams sowohl mit Sommer als auch Winterzeit testen (also wahrscheinlich freezegun aus Projekt Play)
def test_timezone_submit(client):
    #TODO
    # feld erstellen, prüfen ob tz richtig angezeigt wird
    # auch prüfen ob es richtig gespeichert wird - in der Datenbank ist CEST, also: Zeit speichern, Zeit lesen. gelesene Zeit muss gleich gespeicherte Zeit sein
    # feld kreuzen, neu laden, prüfen ob tz bei den feldern richtig ist
    pass


def test_cheater_prevention(client):
    #TODO
    # feld erstellen, sofort fünf Kreuze machen -> Fehler, Feld wird gelöscht
    # dito nochmal mit 5 kreuzen nach 1:55 Stunden
    # dito mit 2 kreuzen nach 1:55 und drei kreuzen nach 2:05, die müssen durchgehen!
    pass


def test_bingo_scoring(client):
    #TODO
    # feld erstellen und 5 kreuze setzen nach 3 Stunden (Score mit Erwartung vergleichen
    # dito mit 5 Stunden, 24 Stunden, 48 Stunden, 96 Stunden, 300 Stunden, 700 Stunden (danach ist der Cookie abgelaufen)
    pass
