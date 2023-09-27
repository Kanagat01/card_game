from django.urls import path
from .views import *

urlpatterns = [
    path('player/create/', CreatePlayer.as_view(), name='create_player'),
    path('game/create/', CreateGame.as_view(), name='create_game'),
    path('review/create/', CreateReview.as_view(), name='create_review'),
]
