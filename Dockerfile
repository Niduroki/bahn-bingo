FROM python:3-slim

RUN mkdir /dbakel/
WORKDIR /dbakel/
COPY . /dbakel/

RUN apt-get update && apt-get install -y gcc && pip install -r /dbakel/requirements.txt

EXPOSE 8000

RUN useradd uwsgi && chown -R uwsgi /dbakel
USER uwsgi

VOLUME ["/dbakel/db/"]

CMD [ "uwsgi", "dbakel-py.ini"]
