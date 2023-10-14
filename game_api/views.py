from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import *


class CreateGame(generics.CreateAPIView):
    serializer_class = GameSerializer
    permission_classes = (AllowAny,)


class CreatePlayer(generics.CreateAPIView):
    serializer_class = PlayerSerializer
    permission_classes = (AllowAny,)


class CreateReview(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (AllowAny,)
