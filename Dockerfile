FROM python:3.8-slim

RUN mkdir /dbakel/
WORKDIR /dbakel/
COPY . /dbakel/

RUN apt-get update && apt-get install -y gcc && pip install -r /dbakel/requirements.txt

EXPOSE 80

CMD [ "uwsgi", "dbakel-py.ini"]