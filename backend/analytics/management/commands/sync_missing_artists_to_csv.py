from django.core.management.base import BaseCommand
from tracker.models import Artist
from analytics.services.calculations import register_unclassified_artists_batch

class Command(BaseCommand):
    help = "Quet toan bo nghe si trong co so du lieu va bo sung vao file CSV neu chua co voi mac dinh 0 va note la New"

    def handle(self, *args, **options):
        artist_names = list(Artist.objects.values_list("name", flat=True))
        total_db = len(artist_names)
        self.stdout.write(f"Tong so nghe si trong co so du lieu: {total_db}")

        added_count = register_unclassified_artists_batch(artist_names)
        self.stdout.write(
            self.style.SUCCESS(
                f"Hoan tat dong bo: da them {added_count} nghe si moi vao file CSV voi gia tri 0 va note la New."
            )
        )
