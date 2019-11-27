from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from flask import current_app

Base = declarative_base()


class BingoField(Base):
    __tablename__ = "bingofield"

    id = Column(Integer, primary_key=True)
    link = Column(String)
    uuid = Column(String)
    player_name = Column(String)
    start_time = Column(DateTime)
    finished = Column(Boolean)
    score = Column(Integer)  # 1.000.000/minutes taken

    def __repr__(self):
        return f"ID: {self.id}, Game by {self.player_name} with link {self.link}"


class BingoSquares(Base):
    __tablename__ = "bingosquares"

    id = Column(Integer, primary_key=True)
    bingo_field_id = Column(Integer, ForeignKey('bingofield.id'))
    content = Column(String)
    check_time = Column(DateTime)
    x_position = Column(Integer)
    y_position = Column(Integer)

    bingo_field = relationship("BingoField", back_populates="squares")

    def __repr__(self):
        return f"ID: {self.id}, for field id: {self.bingo_field_id}, pos: " + \
            f"{self.x_position}x{self.y_position}, check_time {self.check_time}"


BingoField.squares = relationship("BingoSquares", back_populates="bingo_field")


def get_session():
    try:
        db_uri = current_app.config["DATABASE"]
    except KeyError:
        db_uri = 'sqlite:///db/bingo.db'
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
