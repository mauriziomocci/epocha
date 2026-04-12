"""Management command to clean up stale ExtractionCache entries.

Deletes cache entries older than a configurable threshold that have
not been reused (hit_count at or below a threshold) and are not
referenced by any active KnowledgeGraph. This prevents unbounded
growth of the extraction cache table over time.

Usage:
    python manage.py cleanup_extraction_cache
    python manage.py cleanup_extraction_cache --min-age-days 60
    python manage.py cleanup_extraction_cache --dry-run
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from epocha.apps.knowledge.models import ExtractionCache


class Command(BaseCommand):
    help = "Delete stale ExtractionCache entries not referenced by any active graph."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age-days",
            type=int,
            default=30,
            help="Minimum age in days before an entry is eligible for deletion (default: 30).",
        )
        parser.add_argument(
            "--max-hit-count",
            type=int,
            default=0,
            help="Maximum hit_count for an entry to be eligible for deletion (default: 0).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show how many entries would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        min_age_days = options["min_age_days"]
        max_hit_count = options["max_hit_count"]
        dry_run = options["dry_run"]

        cutoff = timezone.now() - timedelta(days=min_age_days)

        candidates = ExtractionCache.objects.filter(
            created_at__lt=cutoff,
            hit_count__lte=max_hit_count,
        ).exclude(
            # Keep entries still referenced by at least one graph
            graphs__isnull=False,
        )

        count = candidates.count()

        if dry_run:
            self.stdout.write(
                f"Dry run: {count} cache entries would be deleted "
                f"(older than {min_age_days} days, hit_count <= {max_hit_count}, no active graphs)."
            )
            return

        deleted, _ = candidates.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} stale cache entries "
                f"(older than {min_age_days} days, hit_count <= {max_hit_count}, no active graphs)."
            )
        )
