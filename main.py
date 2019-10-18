from flask import Flask, render_template, request, redirect, make_response, url_for
from uuid import uuid4
from string import ascii_lowercase
from random import choice, shuffle
from datetime import datetime
import db
from reasons import reasons
from itertools import carthesian_product

app = Flask(__name__)

def generate_string(len=10):
    retval = ""
    for i in range(0,len):
        retval += choice(ascii_lowercase)
    return retval

def create_squares(bingo_id, session):
    shuffled_reasons = reasons.copy()
    shuffle(shuffled_reasons)
    objs = []
    for x,y in carthesian_product([1,2,3,4,5],[1,2,3,4,5]):
        if x == y == 3:
            objs.append(
                db.BingoSquares(
                    x_position=x, y_position=y, bingo_field_id=bingo_id,
                    content="Heute ca. 5 Minuten später"
                )
            )
        objs.append(
            db.BingoSquares(
                x_position=x, y_position=y, bingo_field_id=bingo_id,
                content=shuffled_reasons.pop()
            )
        )
    session.add_bulk(objs)
    session.commit()


@app.route('/', methods=["get", "post"])
def index():
    if request.method == "GET":
        session = db.Session()
        if request.cookies.get("bingo_uuid") is not None:
            try:
                instance = session.query(db.BingoField).filter_by(
                    uuid=request.cookies.get("bingo_uuid")
                ).one()
            except:
                response = make_response(url_for('.index'))
                response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
                return response
            return redirect(url_for('.bingo_field', bingo_str=instance.link))
        else:
            games = session.query(db.BingoField).all()
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

        response = make_response(redirect(url_for('.bingo_field', bingo_str=obj.link)))
        response.set_cookie(
            key="bingo_uuid", value=obj.uuid, max_age=3600*24*90,  # 90 days
        )
        return response

@app.route('/<string:bingo_str>/')
def bingo_field(bingo_str):
    session = db.Session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except:
        return 404

    # authentification via uuid-cookie
    authenticated = False

    if authenticated:
        pass
    else:
        return render_template(
            "field.html", bingo_uuid=bingo_str,
            quit_url=url_for('.bingo_quit', bingo_str=bingo_str),
            submit_url_base=url_for('.bingo_field', bingo_str=bingo_str)+"submit/",
        )

@app.route('/<string:bingo_str>/quit/')
def bingo_quit(bingo_str):
    session = db.Session()
    try:
        obj = session.query(db.BingoField).filter_by(link=bingo_str).one()
    except:
        return 404

    # authentification via uuid-cookie
    authenticated = True
    if not authenticated:
        return 403

    obj.finished = True
    session.commit()

    response = make_response(redirect('/'))
    response.set_cookie(key="bingo_uuid", value="", expires=0)  # set cookie to expire
    return response

@app.route('/<string:bingo_str>/submit/<int:field>/', methods=["post"])
def bingo_submit(bingo_str, field):
    if not 1 <= field <= 25:
        return "fehler!"

    # authentification via uuid-cookie
    authenticated = True
    if not authenticated:
        return 403

    return "ajax, ja/nein"

@app.route('/highscores/')
def highscores():
    return render_template("highscores.html")
