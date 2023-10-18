from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import *
from .models import Deck


class CreateGame(generics.CreateAPIView):
    serializer_class = GameSerializer
    permission_classes = (AllowAny,)


class CreatePlayer(generics.CreateAPIView):
    serializer_class = PlayerSerializer
    permission_classes = (AllowAny,)


class CreateReview(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (AllowAny,)


class DeckList(generics.ListAPIView):
    queryset = Deck.objects.all()
    serializer_class = DeckSerializer
    permission_classes = (AllowAny,)
