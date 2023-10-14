#!/bin/bash

source /root/venv/bin/activate
cd /root/card_game/

uwsgi --ini config/uwsgi/uwsgi.ini &
daphne -u /tmp/daphne.sock -p 8000 card_game.asgi:application