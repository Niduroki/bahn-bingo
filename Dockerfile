FROM python:3-alpine

RUN apk add --no-cache gcc g++ libc-dev linux-headers

RUN mkdir /dbakel/
WORKDIR /dbakel/
COPY . /dbakel/

ENV VIRTUAL_ENV=/dbakel/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

EXPOSE 8000

RUN adduser -S uwsgi && chown -R uwsgi /dbakel
USER uwsgi
RUN pip install --no-cache-dir -r /dbakel/requirements.txt

VOLUME ["/dbakel/db/"]

CMD [ "uwsgi", "dbakel-py.ini"]
