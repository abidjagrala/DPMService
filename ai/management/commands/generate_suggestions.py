from django.core.management.base import BaseCommand

from ai.suggestions import generate_suggestions


class Command(BaseCommand):
    help = 'Generate AI-powered suggestions for the dashboard'

    def handle(self, *args, **options):
        suggestions = generate_suggestions()
        self.stdout.write(self.style.SUCCESS(f'Generated {len(suggestions)} suggestions'))
