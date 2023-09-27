import random
import json

from channels.generic.websocket import WebsocketConsumer
from django.db.models import Max
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import *


class GameWaitingConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        self.send_players_info()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        player_id = data["player_id"]
        player = Player.objects.get(id=player_id)
        status = data['status']
        player.status = status
        player.save()

        self.scope['session']['player_id'] = player_id

        self.send_players_info()

    def send_players_info(self):
        game_id = self.scope['url_route']['kwargs']['game_id']
        game = Game.objects.get(id=game_id)

        isReadyToPlay = game.players.count() == game.members_num

        members = {}
        for x in game.players.all():
            members[x.id] = {'avatar': x.avatar, 'status': x.status}

            if x.status != PlayerStatus.READY:
                isReadyToPlay = False

        data = {'members': members, 'isReadyToPlay': isReadyToPlay}
        self.send(text_data=json.dumps(data))


class GamePrivateConsumer(WebsocketConsumer):
    def connect(self):
        pl_id = self.scope['session']['player_id']
        pl_id_from_url = self.scope['url_route']['kwargs']['game_id']
        if pl_id == pl_id_from_url:
            self.accept()
            self.player = Player.objects.get(id=pl_id)
            self.room_name = f"player_{pl_id}"
            self.channel_layer = get_channel_layer()
            async_to_sync(self.channel_layer.group_add)(
                self.room_name,
                self.channel_name,
            )
        else:
            self.close(code=4000)

    def disconnect(self, code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        round_num = self.scope['session']['round_num']
        round = Round.objects.get(self.player.game.round.get(round_num=round_num))

        if 'association_card' in data:
            card = Card.objects.get(id=data['association_card'])
            Association.objects.create(player=self.player, round=round, card=card)

        elif 'choice' in data:
            self.player.status = PlayerStatus.READY
            self.player.save()
            card = Card.objects.get(id=data['choice'])
            Choice.objects.update_or_create(round=round, player=self.player, card=card)

            all_players_ready = is_all_ready(self.player)
            if all_players_ready:
                async_to_sync(self.channel_layer.group_send)("public_room", {
                    "type": "calculate_results",
                    "game": self.player.game
                })

    def send_player_info(self):
        self.scope['session']['round_num'] = Round.objects.aggregate(
                max_round=Max('round_num'))['max_round']
        round = Round.objects.get(
            game=self.player.game, round_num=self.scope['session'])

        player_cards = PlayerCard.objects.filter(player=self.player)
        player_cards = {obj.card.id: obj.card.img.url for obj in player_cards}

        players = round.game.players.exclude(id=self.player.id)
        players = {obj.id: {'avatar': obj.avatar, 'status': obj.status,
                            'points': obj.points} for obj in players}

        data = {'game_status': self.player.game.status,
                'leader_id': round.leader.id, 'player_cards': player_cards, 'players': players}
        self.send(text_data=json.dumps(data))

    def send_ready_and_points_info(self):
        players = self.player.game.players.exclude(id=self.player.id)
        data = {obj.id: {'status': obj.status, 'points': obj.points}
                for obj in players}
        self.send(text_data=json.dumps(data))
         
    def send_chosen_cards(self):
        round = Round.objects.get(game=Player.game)
        for pl in round.game.players.exclude(id=round.leader.id):
            pl.status = PlayerStatus.NOT_READY
            pl.save()
        pl.leader.status = PlayerStatus.READY
        pl.save()

        placeCards = {obj.card.id: obj.card.img.url for obj in Round.associations.all()}
        pl_card = self.player.associations.get(round=round).card.id
        data = {'your_card': pl_card, 'placeCards': placeCards}
        self.send(text_data=json.dumps(data))


class GamePublicConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        game_id = self.scope['url_route']['kwargs']['game_id']
        game = Game.objects.get(id=game_id)
        game.status = GameStatus.PLAYING

        self.create_round(round_num=1, game=game)

        self.room_name = "public_room"
        self.channel_layer = get_channel_layer()
        async_to_sync(self.channel_layer.group_add)(
                self.room_name,
                self.channel_name,
        )

    def disconnect(self, code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)

        player_id = self.scope['session']['player_id']
        player = Player.objects.get(id=player_id)

        round_num = self.scope['session']['round_num']
        round = player.game.rounds.get(round_num=round_num)

        if 'association_text' in data and player == round.leader:
            player.status = PlayerStatus.READY
            player.save()

            round.association_text = data['association_text']
            round.save()
            Association.objects.create(player=player, round=round,
                                       card=Card.objects.get(data['association_card']))

            for player in player.game.players.exclude(id=player_id):
                player.status = PlayerStatus.NOT_READY
                player.save()

            data = {'association_text': round.association_text}
            self.send(text_data=json.dumps(data))

        elif 'status' in data:
            player.status = data['status']
            player.save()

            async_to_sync(self.channel_layer.group_send)(f"player_{round.leader.id}", {
                "type": "send_ready_and_points_info"
            })

            all_players_ready = is_all_ready(player)

            if all_players_ready:
                for player in player.game.players.all():
                    async_to_sync(self.channel_layer.group_send)(f"player_{player.id}", {
                        "type": "send_chosen_cards"
                    })

    def random_card_for_each_players(self, game, selected_cards):
        for player in game.players.all():
            cards = random.sample(selected_cards, 3)
            if player.cards.count() != 0:
                for card in player.cards.all():
                    card.delete()
            for card in cards:
                PlayerCard.objects.create(player=player, card=card)
            async_to_sync(self.channel_layer.group_send)(f"player_{player.id}", {
                        "type": "send_player_info"
                    })
    
    def calculate_results(self, game):
        players = game.players.all()
        round = Round.objects.get(game=game, round_num=self.scope['session']['round_num'])
        winner = None
        for pl in players:
            association = Association.objects.get(round=round, player=pl)
            choices = Choice.objects.filter(card=association.card)
            data = {}
            
            if pl == round.leader:
                points = 0
                who_chose = []
                if choices.exists() and choices.count() != players.count():
                    points += 3 + choices.count()
                    pl.points += points
                    who_chose = [ch.player.id for ch in choices]

            else:
                leader_association = Association.objects.get(round=round, player=round.leader)
                pl_association = Association.objects.get(round=round, player=pl)
                pl_choice = Choice.objects.get(round=round, player=pl) 
                points = 0
                guess_right = False

                if leader_association.card == pl_choice.card:
                    points += 3
                    guess_right = True

                choices = Choice.objects.filter(card=pl_association.card)
                points += choices.count()
                who_chose = [ch.player.id for ch in choices]
                data.update({'guess_right': guess_right})

            pl.points += points
            data.update({"who_chose_your_cards": who_chose, "points_for_round": points, "all_points": pl.points})
            
            async_to_sync(self.channel_layer.group_send)(f"player_{pl.id}", {
                "type": "send",
                "text_data": json.dumps(data)
            })

            if pl.points >= pl.game.points_to_win:
                winner = pl

        if winner:
            winner.game.status = GameStatus.FINISHED
            game.winner = winner
            winner.game.save()
            self.send(text_data=json.dumps({'winner_id': winner.id}))
        else:
            self.create_round(round_num=self.scope['session']['round_num'], game=game)

    def create_round(self, round_num, game):
        try:
            round = Round.objects.get(game=game, round_num=round_num)
        except:
            Round.objects.create(game=game, round_num=round_num,
                             leader=random.choice(game.players.all()))

        cards_count = game.members_num * 4
        selected_cards = random.sample(game.deck.cards.all(), cards_count)
        for card in selected_cards:
            GameCard.objects.create(game=game, card=card)
        self.random_card_for_each_players(game, selected_cards)


def is_all_ready(player):
    all_players_ready = True
    for x in player.game.players.exclude(id=player.id):
        if x.status != PlayerStatus.READY:
            all_players_ready = False
    return all_players_ready