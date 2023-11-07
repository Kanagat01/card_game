import random
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Max
from .models import *


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        game = await database_sync_to_async(Game.objects.get)(
            id=self.game_id
        )
        try:
            self.round_num = await get_round_num(game)
        except:
            pass

        player_id = self.scope['url_route']['kwargs']['player_id']
        self.player = await database_sync_to_async(Player.objects.get)(
            id=player_id
        )

        self.room_group_name = f"player_{self.player.id}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.channel_layer.group_add(
            "public_room",
            self.channel_name
        )
        await self.accept()
        await self.send_status_info()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            "public_room",
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        game = await database_sync_to_async(Game.objects.get)(
            id=self.game_id
        )

        if game.status == GameStatus.WAITING:
            if "game_status" in data:
                if data["game_status"] == GameStatus.PLAYING:
                    game.status = data["game_status"]
                    await database_sync_to_async(game.save)()
                    await self.channel_layer.group_send(
                        "public_room",
                        {
                            'type': 'send_message',
                            'data': {"game_started": True}
                        }
                    )

            else:
                player_id = data["player_id"]
                player = await database_sync_to_async(Player.objects.get)(id=player_id)
                player.status = data['status']
                await database_sync_to_async(player.save)()
                await self.send_status_info()

        else:
            creator_id = await database_sync_to_async(lambda: game.creator.id)()
            if 'create_round' in data and self.player.id == creator_id:
                if data['create_round']:
                    try:
                        self.round_num = await get_round_num(game) + 1
                    except:
                        self.round_num = 1
                    await self.create_round(round_num=self.round_num, game=game)

            else:
                round = await database_sync_to_async(Round.objects.get)(
                    round_num=self.round_num,
                    game=game,
                )
                leader = await database_sync_to_async(lambda: round.leader)()

            if 'association_card' in data:
                self.player.status = PlayerStatus.READY
                await database_sync_to_async(self.player.save)()

                card = await database_sync_to_async(
                    lambda: Card.objects.get(id=data['association_card'])
                )()
                try:
                    association = await database_sync_to_async(Association.objects.get)(
                        player=self.player,
                        round=round
                    )
                    await database_sync_to_async(association.update)(
                        card=card
                    )
                except:
                    await database_sync_to_async(Association.objects.create)(
                        player=self.player,
                        round=round,
                        card=card
                    )

                if self.player == leader:
                    round.association_text = data['association_text']
                    await database_sync_to_async(round.save)()
                    players = await database_sync_to_async(
                        lambda: list(
                            game.players.exclude(id=self.player.id))
                    )()
                    for player in players:
                        player.status = PlayerStatus.NOT_READY
                        await database_sync_to_async(player.save)()

                    data = {'association_text': round.association_text}
                    await self.channel_layer.group_send(
                        "public_room",
                        {
                            'type': 'send_message',
                            'data': data
                        }
                    )
                    await self.send_ready_and_points_info()
                else:
                    await self.send_ready_info()
                    all_players_ready = await is_all_ready(game)

                    if all_players_ready:
                        players = await database_sync_to_async(
                            lambda: list(game.players.all())
                        )()
                        for player in players:
                            await self.channel_layer.group_send(
                                f"player_{player.id}",
                                {
                                    'type': 'send_chosen_cards',
                                }
                            )

            elif 'choice' in data:
                self.player.status = PlayerStatus.READY
                await database_sync_to_async(self.player.save)()

                card = await database_sync_to_async(Card.objects.get)(id=data['choice'])

                try:
                    choice = await database_sync_to_async(Choice.objects.get)(
                        round=round,
                        player=self.player
                    )
                    choice.card = card
                    await database_sync_to_async(choice.save)()

                except Choice.DoesNotExist:
                    await database_sync_to_async(Choice.objects.create)(
                        round=round,
                        player=self.player,
                        card=card
                    )
                await self.send_ready_info()
                all_players_ready = await is_all_ready(game)

                if all_players_ready:
                    await self.channel_layer.group_send(
                        f"player_{self.player.id}",
                        {
                            "type": "calculate_results"
                        }
                    )

    async def send_status_info(self):
        game_id = self.scope['url_route']['kwargs']['game_id']
        game = await database_sync_to_async(Game.objects.get)(id=game_id)

        isReadyToPlay = await database_sync_to_async(game.players.count)() == game.members_num
        members = {}
        players = await database_sync_to_async(list)(game.players.all())
        for x in players:
            members[str(x.id)] = {'avatar': x.avatar, 'status': x.status}

            if x.status != PlayerStatus.READY:
                isReadyToPlay = False

        data = {'members': members, 'isReadyToPlay': isReadyToPlay}

        await self.channel_layer.group_send(
            "public_room",
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def send_player_info(self, event):
        game = await database_sync_to_async(Game.objects.get)(
            id=self.game_id
        )
        self.round_num = await get_round_num(game)

        round = await database_sync_to_async(Round.objects.get)(
            game=game,
            round_num=self.round_num
        )

        player_cards = await database_sync_to_async(
            lambda: list(self.player.cards.all())
        )()
        player_cards = {str(card.id): card.img.url for card in player_cards}

        players = await database_sync_to_async(
            lambda: list(Player.objects.filter(
                game=game).exclude(id=self.player.id))
        )()
        players = {str(obj.id): {'avatar': obj.avatar, 'status': obj.status,
                                 'points': obj.points} for obj in players}
        leader_id = await database_sync_to_async(lambda: round.leader.id)()

        data = {'game_status': game.status,
                'leader_id': leader_id, 'player_cards': player_cards, 'players': players}
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def send_ready_and_points_info(self):
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)
        players = await database_sync_to_async(
            lambda: list(game.players.exclude(id=self.player.id))
        )()
        data = {str(obj.id): {'status': obj.status, 'points': obj.points}
                for obj in players}

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def send_ready_info(self):
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)
        players = await database_sync_to_async(
            lambda: list(game.players.all())
        )()
        data = {str(obj.id): obj.status for obj in players}
        await self.channel_layer.group_send(
            "public_room",
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def send_chosen_cards(self, event):
        game = await database_sync_to_async(Game.objects.get)(id=self.game_id)
        round = await database_sync_to_async(Round.objects.get)(game=game, round_num=self.round_num)
        players = await database_sync_to_async(
            lambda: list(game.players.exclude(id=round.leader.id))
        )()

        for pl in players:
            pl.status = PlayerStatus.NOT_READY
            await database_sync_to_async(pl.save)()

        leader = await database_sync_to_async(lambda: round.leader)()
        leader.status = PlayerStatus.READY
        await database_sync_to_async(round.save)()

        pl_card = await database_sync_to_async(
            lambda: Association.objects.get(
                player=self.player, round=round).card.id
        )()
        association_cards = await database_sync_to_async(
            lambda: [
                obj.card for obj in round.associations.exclude(card=pl_card)]
        )()
        placeCards = {
            str(card.id): card.img.url for card in association_cards
        }

        data = {'your_card': pl_card, 'placeCards': placeCards}
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def calculate_results(self, event):
        game = await database_sync_to_async(Game.objects.get)(
            id=self.game_id
        )
        players = await database_sync_to_async(
            lambda: list(Player.objects.filter(game=game))
        )()
        self.round_num = await get_round_num(game)
        for player in players:
            round = await database_sync_to_async(Round.objects.get)(
                game=game,
                round_num=self.round_num
            )
            association = await database_sync_to_async(Association.objects.get)(
                round=round,
                player=player
            )
            choices = await database_sync_to_async(
                lambda: list(Choice.objects.filter(
                    card=association.card, round=round))
            )()
            data = {}

            leader = await database_sync_to_async(lambda: round.leader)()
            points = 0

            if player == leader:
                who_chose = []

                choices_count = len(choices)
                players_count = await database_sync_to_async(game.players.count)()

                if 0 < choices_count < players_count - 1:
                    points += 3 + choices_count
                    player.points += points
                    who_chose = await database_sync_to_async(
                        lambda: [ch.player.id for ch in choices]
                    )()

            else:
                leader_association_card = await database_sync_to_async(
                    lambda: Association.objects.get(
                        round=round, player=leader).card
                )()
                pl_choice_card = await database_sync_to_async(
                    lambda: Choice.objects.get(round=round, player=player).card
                )()
                guess_right = False

                if leader_association_card.id == pl_choice_card.id:
                    points += 3
                    guess_right = True

                points += len(choices)
                player.points += points

                who_chose = await database_sync_to_async(lambda: [ch.player.id for ch in choices])()
                data.update({'guess_right': guess_right})

            await database_sync_to_async(player.save)()

            data.update({"who_chose_your_cards": who_chose,
                        "points_for_round": points, "all_points": player.points})

            if player.points >= game.points_to_win:
                game.status = GameStatus.FINISHED
                if game.winner:
                    game.winner = await database_sync_to_async(
                        lambda: player if player.points > game.winner.points else game.winner
                    )()
                else:
                    game.winner = player
                await database_sync_to_async(game.save)()

            await self.channel_layer.group_send(
                f"player_{player.id}",
                {
                    'type': 'send_message',
                    'data': data
                }
            )

        winner = await database_sync_to_async(lambda: game.winner)()
        if winner:
            await self.channel_layer.group_send(
                "public_room",
                {
                    "type": "send_message",
                    "data": {"winner": winner.id}
                }
            )

    async def create_round(self, round_num, game):
        players = await database_sync_to_async(list)(game.players.all())
        for player in players:
            player.status = PlayerStatus.NOT_READY
            await database_sync_to_async(player.save)()
        await database_sync_to_async(Round.objects.create)(
            game=game,
            round_num=round_num,
            leader=random.choice(players)
        )
        cards_count = game.members_num * 4
        all_cards = await database_sync_to_async(
            lambda: list(Card.objects.filter(deck=game.deck))
        )()

        selected_cards = random.sample(all_cards, cards_count)
        for card in selected_cards:
            await database_sync_to_async(game.cards.add)(card)
        await self.random_card_for_each_players(game, selected_cards, players)

    async def random_card_for_each_players(self, game, selected_cards, players):
        for player in players:
            cards = random.sample(selected_cards, 4)

            cards_count = await database_sync_to_async(player.cards.count)()

            if cards_count != 0:
                player_cards = await database_sync_to_async(list)(player.cards.all())
                for card in player_cards:
                    await database_sync_to_async(lambda: player.cards.remove(card))()

            for card in cards:
                selected_cards.remove(card)
                player_cards_list = []

                player_card = await database_sync_to_async(player.cards.add)(card)
                player_cards_list.append(player_card)
            await self.channel_layer.group_send(
                f"player_{player.id}",
                {
                    'type': 'send_player_info'
                }
            )

    async def send_message(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))


@database_sync_to_async
def is_all_ready(game):
    all_players_ready = True
    for x in game.players.all():
        if x.status == PlayerStatus.NOT_READY:
            all_players_ready = False
    return all_players_ready


@database_sync_to_async
def get_round_num(game):
    result = Round.objects.filter(game=game).aggregate(
        max_round=Max('round_num'))
    return result['max_round']
