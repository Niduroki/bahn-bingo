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

app = Flask(__name__)


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
            print(reason)
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
        session = db.Session()
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

        session = db.Session()
        obj = db.BingoField(
            link=generate_string(), uuid=str(uuid4()), player_name=player_name,
            finished=False, start_time=datetime.now()
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
    session = db.Session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except NoResultFound:
        abort(404)

    user_uuid = request.cookies.get("bingo_uuid")
    if user_uuid is not None and user_uuid == obj.uuid:
        authenticated = True
    else:
        authenticated = False

    if authenticated:
        pass

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


@app.route('/<link:bingo_str>/quit/')
def bingo_quit(bingo_str):
    session = db.Session()
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

    response = make_response(redirect('/'))
    response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
    return response


@app.route('/<link:bingo_str>/submit/<int:x>/<int:y>/', methods=["post"])
def bingo_submit(bingo_str, x, y):
    if not 1 <= x <= 5 or not 1 <= y <= 5:
        return jsonify(data="error")

    session = db.Session()
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

    square.check_time = datetime.now()
    session.commit()

    if check_bingo(session, field):
        field.finished = True
        score = field.start_time - datetime.now()
        field.score = int(1000000 / max(score.seconds//60, 1))
        session.commit()

        return jsonify(data="finished", score=int(1000000 / max(score.seconds//60, 1)))

    return jsonify(data="success", x=x, y=y)


@app.route('/<link:bingo_str>/submit/<int:x>/<int:y>/undo/', methods=["post"])
def bingo_undo(bingo_str, x, y):
    if not 1 <= x <= 5 or not 1 <= y <= 5:
        return jsonify(data="error")

    session = db.Session()
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
    session = db.Session()
    games = session.query(db.BingoField).order_by(db.BingoField.score.desc()).all()
    return render_template("highscores.html", games=games)
