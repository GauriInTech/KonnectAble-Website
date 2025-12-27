from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Toggle ENABLE_CLAUDE_HAIKU_4_5 in project .env file (use "on" or "off").'

    def add_arguments(self, parser):
        parser.add_argument('state', choices=['on', 'off'], help='"on" to enable, "off" to disable')

    def handle(self, *args, **options):
        state = options['state']
        val = 'true' if state == 'on' else 'false'
        env_path = Path(settings.BASE_DIR) / '.env'
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines()

        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('ENABLE_CLAUDE_HAIKU_4_5='):
                lines[i] = f'ENABLE_CLAUDE_HAIKU_4_5={val}'
                updated = True
                break

        if not updated:
            lines.append(f'ENABLE_CLAUDE_HAIKU_4_5={val}')

        env_path.write_text('\n'.join(lines) + ('\n' if lines and not lines[-1].endswith('\n') else ''))

        self.stdout.write(self.style.SUCCESS(f'Wrote {env_path} with ENABLE_CLAUDE_HAIKU_4_5={val}'))
        self.stdout.write('Restart the server/process to apply the change.')
