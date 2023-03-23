from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase, Mapped, mapped_column
from flask import current_app
from datetime import datetime
from typing import List


class Base(DeclarativeBase):
    pass


class BingoField(Base):
    __tablename__ = "bingofield"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str]
    uuid: Mapped[str]
    player_name: Mapped[str]
    start_time: Mapped[datetime]
    finished: Mapped[bool]
    score: Mapped[int]  # 1.000.000/minutes taken

    squares: Mapped[List['BingoSquares']] = relationship(back_populates="bingo_field")

    def __repr__(self):
        return f"ID: {self.id}, Game by {self.player_name} with link {self.link}"


class BingoSquares(Base):
    __tablename__ = "bingosquares"

    id: Mapped[int] = mapped_column(primary_key=True)
    bingo_field_id: Mapped[int] = mapped_column(ForeignKey('bingofield.id'))
    content: Mapped[str]
    check_time: Mapped[datetime]
    x_position: Mapped[int]
    y_position: Mapped[int]

    bingo_field = relationship("BingoField", back_populates="squares")

    def __repr__(self):
        return f"ID: {self.id}, for field id: {self.bingo_field_id}, pos: " + \
            f"{self.x_position}x{self.y_position}, check_time {self.check_time}"


def get_session():
    try:
        db_uri = current_app.config["DATABASE"]
    except KeyError:
        db_uri = 'sqlite:///db/bingo.db'
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
