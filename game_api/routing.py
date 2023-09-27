from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/game/waiting/(?P<game_id>\d+)/$",
            consumers.GameWaitingConsumer.as_asgi()),
    re_path(r"ws/game/playing/(?P<game_id>\d+)/$",
            consumers.GamePublicConsumer.as_asgi()),
    re_path(r"ws/game/playing/(?P<game_id>\d+)/(?P<player_id>\d+)/$",
            consumers.GamePrivateConsumer.as_asgi())
]
