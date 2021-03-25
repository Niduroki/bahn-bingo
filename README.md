Bahn-Bingo
----------

[![Build Status](https://drone.niduroki.net/api/badges/niduroki/bahn-bingo/status.svg)](https://drone.niduroki.net/niduroki/bahn-bingo)

Wir bitten um ihr Verständnis.

-----------

## Docker

Expose port 8000.
Volume `/dbakel/db` für Datenbank.

### Update notes

De-Rooted this image on 2021-03-21, you need to to a `chown -R 1000 volume-dir` on your volume directory for the data, sometime before or after the next update.
