FROM python:3-slim

RUN mkdir /dbakel/
WORKDIR /dbakel/
COPY . /dbakel/

RUN apt-get update && apt-get install -y gcc
ENV VIRTUAL_ENV=/dbakel/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

EXPOSE 8000

RUN useradd uwsgi && chown -R uwsgi /dbakel
USER uwsgi
RUN pip install --no-cache-dir -r /dbakel/requirements.txt

VOLUME ["/dbakel/db/"]

CMD [ "uwsgi", "dbakel-py.ini"]
