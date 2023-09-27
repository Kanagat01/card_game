from django.shortcuts import render
from rest_framework import generics
from .serializers import *


class CreateGame(generics.CreateAPIView):
    serializer_class = GameSerializer


class CreatePlayer(generics.CreateAPIView):
    serializer_class = PlayerSerializer


class CreateReview(generics.CreateAPIView):
    serializer_class = ReviewSerializer

