from django.db import models
from PIL import Image


class PlayerStatus(models.TextChoices):
    NOT_READY = 'NR', 'Not Ready'
    READY = 'RD', 'Ready'


class Player(models.Model):
    game = models.ForeignKey(
        'Game', on_delete=models.CASCADE, related_name='players', null=True, blank=True)
    avatar = models.CharField(max_length=255)
    status = models.CharField(
        max_length=2, choices=PlayerStatus.choices, default=PlayerStatus.NOT_READY)
    points = models.IntegerField(default=0)

    def __str__(self):
        return f'Player #{self.id}'


class GameStatus(models.TextChoices):
    WAITING = 'WT', 'Waiting'
    PLAYING = 'PL', 'Playing'
    FINISHED = 'FN', 'Finished'


class Game(models.Model):
    MEMBER_NUM_CHOICES = (
        (3, '3'),
        (4, '4'),
        (5, '5'),
        (6, '6'),
    )

    creator = models.OneToOneField(
        Player, on_delete=models.CASCADE, related_name='created_games')
    deck = models.ForeignKey('Deck', on_delete=models.CASCADE)
    members_num = models.IntegerField(choices=MEMBER_NUM_CHOICES)
    points_to_win = models.IntegerField()
    status = models.CharField(
        max_length=2, choices=GameStatus.choices, default=GameStatus.PLAYING)
    winner = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')

    def __str__(self):
        return f'Game #{self.id}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.creator.game = self
        self.creator.status = PlayerStatus.READY
        self.creator.save()


class Round(models.Model):
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name='rounds')
    round_num = models.PositiveIntegerField()
    leader = models.ForeignKey(Player, on_delete=models.CASCADE)
    association_text = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'{self.game} round_num: {self.round_num}'


class Association(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name='associations')
    round = models.ForeignKey(
        Round, on_delete=models.CASCADE, related_name='associations')
    card = models.ForeignKey('Card', on_delete=models.CASCADE)


class Choice(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name='choices')
    round = models.ForeignKey(
        Round, on_delete=models.CASCADE, related_name='choices')
    card = models.ForeignKey('Card', on_delete=models.CASCADE)


class Deck(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Card(models.Model):
    deck = models.ForeignKey(
        Deck, on_delete=models.CASCADE, related_name='cards')
    img = models.ImageField(upload_to='cards/')
    players = models.ManyToManyField(
        'Player', related_name='cards', blank=True)
    games = models.ManyToManyField(
        'Game', related_name='cards', blank=True)

    def __str__(self):
        return f'{self.deck} card_num: {self.id}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.img.path)

        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.img.path)


class Review(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    visual = models.IntegerField()
    gameplay = models.IntegerField()
    recomendation = models.IntegerField()
