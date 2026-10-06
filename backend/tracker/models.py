from django.db import models
from django.contrib.auth.models import User

class Artist(models.Model):
    spotify_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    genres = models.JSONField(default=list, blank=True)
    image_url = models.URLField(max_length=512, blank=True, null=True)

    class Meta:
        db_table = 'tracker_artist'
        indexes = [
            models.Index(fields=['spotify_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

class Album(models.Model):
    spotify_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    release_date = models.CharField(max_length=50, blank=True)
    image_url = models.URLField(max_length=512, blank=True, null=True)
    artists = models.ManyToManyField(Artist, related_name='albums')

    class Meta:
        db_table = 'tracker_album'
        indexes = [
            models.Index(fields=['spotify_id']),
        ]

    def __str__(self):
        return self.name

class Track(models.Model):
    spotify_id = models.CharField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    duration_ms = models.IntegerField(default=0)
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='tracks')
    artists = models.ManyToManyField(Artist, related_name='tracks')

    # Audio Features phuc vu Radar Chart & KNN Recommender
    danceability = models.FloatField(default=0.0)
    energy = models.FloatField(default=0.0)
    valence = models.FloatField(default=0.0)
    acousticness = models.FloatField(default=0.0)
    tempo = models.FloatField(default=0.0)
    features_synced = models.BooleanField(default=False)

    class Meta:
        db_table = 'tracker_track'
        indexes = [
            models.Index(fields=['spotify_id']),
            models.Index(fields=['features_synced']),
        ]

    def __str__(self):
        return self.name

class ListeningHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listening_histories')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='play_records')
    played_at = models.DateTimeField(db_index=True)
    context_type = models.CharField(max_length=64, blank=True, null=True)
    raw_spotify_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tracker_listening_history'
        constraints = [
            models.UniqueConstraint(fields=['user', 'played_at'], name='unique_user_track_play')
        ]
        indexes = [
            models.Index(fields=['user', 'played_at']),
            models.Index(fields=['played_at']),
        ]
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.user.username} - {self.track.name} ({self.played_at})"
