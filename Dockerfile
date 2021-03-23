FROM python:3-slim

RUN mkdir /dbakel/
WORKDIR /dbakel/
COPY . /dbakel/

RUN apt-get update && apt-get install -y gcc && pip install -r /dbakel/requirements.txt

EXPOSE 80

RUN useradd dbakel && chown -R dbakel /dbakel
USER dbakel

VOLUME ["/dbakel/db/"]

CMD [ "uwsgi", "dbakel-py.ini"]
