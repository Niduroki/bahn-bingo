from flask import Flask, render_template, request, redirect, make_response, url_for, abort, jsonify
from uuid import uuid4
from string import ascii_lowercase
from random import choice, shuffle
from datetime import datetime
import db
from reasons import reasons
from itertools import product as carthesian_product
from werkzeug.routing import BaseConverter
from sqlalchemy.orm.exc import NoResultFound
from pytz import timezone

app = Flask(__name__)

berlin = timezone("Europe/Berlin")


class LinkConverter(BaseConverter):
    regex = r"[\w]{10}"


app.url_map.converters['link'] = LinkConverter


def generate_string(length=10):
    retval = ""
    for i in range(0, length):
        retval += choice(ascii_lowercase)
    return retval


def create_squares(bingo_id, session):
    shuffled_reasons = reasons.copy()
    shuffle(shuffled_reasons)
    for x, y in carthesian_product([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]):
        if x == y == 3:
            cur = db.BingoSquares(
                x_position=x, y_position=y, bingo_field_id=bingo_id,
                content="Heute ca. 5 Minuten später"
            )
        else:
            reason = shuffled_reasons.pop()
            cur = db.BingoSquares(
                x_position=x, y_position=y, bingo_field_id=bingo_id,
                content=reason
            )
        session.add(cur)
        session.commit()


def check_bingo(session, field):
    # check each row
    for x in range(1, 6):
        count = session.query(db.BingoSquares.check_time).filter(
                db.BingoSquares.bingo_field == field, db.BingoSquares.x_position == x,
                db.BingoSquares.check_time.isnot(None)
        ).count()
        if count == 5:
            return True
    # check each column
    for y in range(1, 6):
        count = session.query(db.BingoSquares.check_time).filter(
            db.BingoSquares.bingo_field == field, db.BingoSquares.y_position == y,
            db.BingoSquares.check_time.isnot(None)
        ).count()
        if count == 5:
            return True
    # check diagonal top left -> bottom right
    count = session.query(db.BingoSquares.check_time).filter(
        db.BingoSquares.bingo_field == field,
        db.BingoSquares.x_position == db.BingoSquares.y_position,
        db.BingoSquares.check_time.isnot(None)
    ).count()
    if count == 5:
        return True
    # check diagonal top right -> bottom left
    count = session.query(db.BingoSquares.check_time).filter(
        db.BingoSquares.bingo_field == field,
        (6-db.BingoSquares.x_position) == db.BingoSquares.y_position,
        db.BingoSquares.check_time.isnot(None)
    ).count()
    if count == 5:
        return True

    return False


@app.route('/', methods=["get", "post"])
def index():
    if request.method == "GET":
        session = db.get_session()
        if request.cookies.get("bingo_uuid") is not None:
            try:
                instance = session.query(db.BingoField).filter_by(
                    uuid=request.cookies.get("bingo_uuid")
                ).one()
            except NoResultFound:
                response = make_response(url_for('.index'))
                response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
                return response
            return redirect(url_for('.bingo_field', bingo_str=instance.link))
        else:
            games = session.query(db.BingoField).filter(
                db.BingoField.score.isnot(None)
            ).order_by(db.BingoField.score.desc()).all()[:5]
            return render_template("index.html", games=games)
    elif request.method == "POST":
        try:
            player_name = request.form['player_name']
        except KeyError:
            return redirect('/')

        session = db.get_session()
        obj = db.BingoField(
            link=generate_string(), uuid=str(uuid4()), player_name=player_name,
            finished=False, start_time=datetime.now(tz=berlin)
        )
        session.add(obj)
        session.commit()

        create_squares(obj.id, session)

        response = make_response(redirect(url_for('.bingo_field', bingo_str=obj.link)))
        response.set_cookie(
            key="bingo_uuid", value=obj.uuid, max_age=3600*24*90,  # 90 days
        )
        return response


@app.route('/<link:bingo_str>/')
def bingo_field(bingo_str):
    session = db.get_session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    user_uuid = request.cookies.get("bingo_uuid")
    if user_uuid is not None and user_uuid == obj.uuid:
        authenticated = True
    else:
        authenticated = False

    if authenticated and obj.finished:
        # Sanity check: Bingo field is done/has been reaped – reset cookie
        response = make_response(redirect('/'))
        response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
        return response

    squares = session.query(db.BingoSquares).filter_by(bingo_field=obj).all()
    field = [['' for x in range(5)] for y in range(5)]  # initialize field
    for square in squares:
        field[square.x_position-1][square.y_position-1] = square

    return render_template(
        "field.html", bingo_uuid=bingo_str,
        quit_url=url_for('.bingo_quit', bingo_str=bingo_str),
        submit_url_base=url_for('.bingo_field', bingo_str=bingo_str)+"submit/",
        authenticated=authenticated, squares=field, bingo=obj,
    )


@app.route('/<link:bingo_str>/hijack/<string:bingo_uuid>/')
def bingo_hijack(bingo_str, bingo_uuid):
    session = db.get_session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    user_uuid = request.cookies.get("bingo_uuid")
    if user_uuid is not None:
        abort(400)
    else:
        if bingo_uuid == obj.uuid:
            response = make_response(redirect(url_for('.bingo_field', bingo_str=obj.link)))
            response.set_cookie(
                key="bingo_uuid", value=obj.uuid, max_age=3600 * 24 * 90,  # 90 days
            )
            return response
        else:
            abort(403)


@app.route('/<link:bingo_str>/quit/', methods=["post"])
def bingo_quit(bingo_str):
    session = db.get_session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    # authentication via uuid-cookie
    user_uuid = request.cookies.get("bingo_uuid")
    if user_uuid is not None and user_uuid == obj.uuid:
        authenticated = True
    else:
        authenticated = False

    if not authenticated:
        abort(403)

    obj.finished = True
    session.commit()

    response = make_response(jsonify(data="success"))
    response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
    return response


@app.route('/<link:bingo_str>/submit/<int:x>/<int:y>/', methods=["post"])
def bingo_submit(bingo_str, x, y):
    if not 1 <= x <= 5 or not 1 <= y <= 5:
        return jsonify(data="error")

    session = db.get_session()
    try:
        field = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    # check authentication via uuid-cookie
    user_uuid = request.cookies.get("bingo_uuid")
    if not (user_uuid is not None and user_uuid == field.uuid):
        abort(403)

    square = session.query(db.BingoSquares).filter_by(
        bingo_field=field, x_position=x, y_position=y
    ).one()

    square.check_time = datetime.now(tz=berlin)
    session.commit()

    if check_bingo(session, field):
        delta = datetime.now(tz=berlin) - field.start_time.astimezone(berlin)
        if delta.total_seconds() <= 7200:
            # Cheater protection - No game can be finished within the first 2 hours
            session.query(db.BingoSquares).filter_by(bingo_field=field).delete()
            session.delete(field)
            session.commit()
            return jsonify(data="cheater")
        else:
            field.finished = True
            field.score = int(1000000 / max(delta.total_seconds()//60, 1))
            session.commit()

            return jsonify(data="finished", score=int(1000000 / max(delta.total_seconds() // 60, 1)))

    return jsonify(data="success", x=x, y=y)


@app.route('/<link:bingo_str>/submit/<int:x>/<int:y>/undo/', methods=["post"])
def bingo_undo(bingo_str, x, y):
    if not 1 <= x <= 5 or not 1 <= y <= 5:
        return jsonify(data="error")

    session = db.get_session()
    try:
        field = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    # check authentication via uuid-cookie
    user_uuid = request.cookies.get("bingo_uuid")
    if not (user_uuid is not None and user_uuid == field.uuid):
        abort(403)

    square = session.query(db.BingoSquares).filter_by(
        bingo_field=field, x_position=x, y_position=y
    ).one()

    square.check_time = None
    session.commit()

    return jsonify(data="success", x=x, y=y)


@app.route('/highscores/')
def highscores():
    session = db.get_session()
    games = session.query(db.BingoField).order_by(db.BingoField.score.desc()).all()
    return render_template("highscores.html", games=games)


@app.route('/active/')
def active():
    session = db.get_session()
    games = session.query(db.BingoField).filter(db.BingoField.finished.isnot(True))
    return render_template("active.html", games=games)


@app.route('/cron/')
def cron():
    session = db.get_session()
    finished = []
    games = session.query(db.BingoField).filter(db.BingoField.finished.isnot(True))
    for game in games:
        timediff = datetime.now(tz=berlin) - game.start_time.astimezone(berlin)
        if timediff.days > 93:  # Check if a game is older than 90 days, i.e. its cookie expired
            # Cookie has expired, quit the game
            game.finished = True
            session.commit()
            finished.append(game.link)
        elif timediff.days > 7:  # Check if a game has no entries after 7 days, i.e. not really started
            checked_fields = session.query(db.BingoSquares.check_time).filter(
                db.BingoSquares.bingo_field == game,
                db.BingoSquares.check_time.isnot(None)
            ).count()
            if checked_fields == 0:
                game.finished = True
                session.commit()
                finished.append(game.link)

    return jsonify(data="success", finished=finished)
