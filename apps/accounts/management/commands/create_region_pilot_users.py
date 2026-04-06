"""
Создание тестовых учёток руководителей по регионам (пилот КГД).

Пример:
  docker compose exec web python manage.py create_region_pilot_users --password 'ВременныйПароль123!'

Повторный запуск: существующие username пропускаются (пароль не меняется).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

REGION_USERS = [
    ("rk_g_almaty", "г.Алматы"),
    ("rk_g_astana", "г.Астана"),
    ("rk_karaganda", "Карагандинская"),
    ("rk_mangystau", "Мангистауская"),
    ("rk_akmola", "Акмолинская"),
    ("rk_atyrau", "Атырауская"),
    ("rk_g_shymkent", "г.Шымкент"),
    ("rk_zhetysu", "Жетысу"),
    ("rk_almaty_reg", "Алматинская"),
    ("rk_turkistan", "Туркестанская"),
    ("rk_aktobe", "Актюбинская"),
    ("rk_kyzylorda", "Кызылординская"),
    ("rk_pavlodar", "Павлодарская"),
    ("rk_zhambyl", "Жамбылская"),
    ("rk_kostanay", "Костанайская"),
    ("rk_vko", "ВКО"),
    ("rk_abay", "Абай"),
    ("rk_ulytau", "Улытау"),
    ("rk_sko", "СКО"),
    ("rk_zko", "ЗКО"),
]


class Command(BaseCommand):
    help = "Создаёт учётки руководителей регионов (роль reviewer) для пилота"

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Начальный пароль для всех новых учёток",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что было бы создано",
        )

    def handle(self, *args, **options):
        password = options["password"]
        dry_run = options["dry_run"]

        if len(password) < 8:
            raise CommandError("Пароль не короче 8 символов")

        created = 0
        skipped = 0

        for username, region_label in REGION_USERS:
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"Уже есть: {username} — пропуск"))
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"[dry-run] создать {username} / {region_label}")
                created += 1
                continue

            User.objects.create_user(
                username=username,
                password=password,
                role="reviewer",
                region=region_label,
                first_name="Руководитель",
                last_name=region_label,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Создан: {username} ({region_label})"))
            created += 1

        self.stdout.write(
            self.style.NOTICE(
                f"Готово: создано {created}, пропущено (уже были) {skipped}."
            )
        )
