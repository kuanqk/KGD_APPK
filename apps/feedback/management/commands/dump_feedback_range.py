"""
Выгрузка обращений по диапазону pk для разбора (ID, вложение, полный текст).

  python manage.py dump_feedback_range --min 64 --max 71
  python manage.py dump_feedback_range --min 64 --max 71 --markdown
"""

from django.core.management.base import BaseCommand

from apps.feedback.models import Feedback


class Command(BaseCommand):
    help = "Вывести обращения Feedback в диапазоне pk (для копирования в таблицу)."

    def add_arguments(self, parser):
        parser.add_argument("--min", type=int, default=64, help="Минимальный pk (включительно)")
        parser.add_argument("--max", type=int, default=71, help="Максимальный pk (включительно)")
        parser.add_argument(
            "--markdown",
            action="store_true",
            help="Таблица Markdown (экранирование | в тексте)",
        )

    def handle(self, *args, **options):
        lo, hi = options["min"], options["max"]
        md = options["markdown"]
        qs = Feedback.objects.filter(pk__gte=lo, pk__lte=hi).order_by("pk")

        rows = []
        for fb in qs:
            file_cell = fb.attachment.name if fb.attachment else ""
            text = (fb.description or "").strip()
            rows.append((fb.pk, file_cell, text))

        if not rows:
            self.stdout.write(self.style.WARNING(f"Нет записей с pk от {lo} до {hi}."))
            return

        if md:
            self.stdout.write("| ID | Файл | Текст |")
            self.stdout.write("| --- | --- | --- |")
            for pk, file_cell, text in rows:
                esc = _md_cell(text)
                fesc = _md_cell(file_cell or "—")
                self.stdout.write(f"| {pk} | {fesc} | {esc} |")
        else:
            for pk, file_cell, text in rows:
                self.stdout.write("-" * 80)
                self.stdout.write(f"ID: {pk}")
                self.stdout.write(f"Файл: {file_cell or '—'}")
                self.stdout.write("Текст:")
                self.stdout.write(text)
                self.stdout.write("")

        self.stdout.write(self.style.NOTICE(f"\nВсего: {len(rows)}"))


def _md_cell(s: str) -> str:
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")

