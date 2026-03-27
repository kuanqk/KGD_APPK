import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

_IIN_BIN_REGEX = re.compile(r'^\d{12}$')

# Мобильные коды операторов РК (первые 4 цифры после +7)
_MOBILE_PREFIXES = {
    '7700', '7701', '7702', '7705', '7706', '7707', '7708', '7709',
    '7710', '7711', '7712', '7713', '7714', '7715', '7716', '7717',
    '7718', '7719', '7720', '7721', '7722', '7723', '7724', '7725',
    '7726', '7727', '7728', '7729',
    '7750', '7751', '7760', '7761', '7762', '7763', '7764', '7765',
    '7771', '7775', '7776', '7777', '7778',
}


@dataclass
class ValidationResult:
    valid: bool
    type: Optional[str] = None        # "IIN" | "BIN" | "mobile" | "landline"
    value: Optional[str] = None       # нормализованное значение
    error: Optional[str] = None       # код ошибки
    metadata: dict = field(default_factory=dict)


class KZValidator:
    """Валидатор казахстанских ИИН/БИН и телефонных номеров."""

    # ── ИИН/БИН ──────────────────────────────────────────────────────────────

    @classmethod
    def validate_iin_bin(cls, number: str) -> ValidationResult:
        """Определяет тип (IIN/BIN) и делегирует соответствующему методу."""
        number = number.strip()
        if not _IIN_BIN_REGEX.match(number):
            return ValidationResult(valid=False, error="invalid_format")

        digits = [int(d) for d in number]
        if not cls._check_control(digits):
            return ValidationResult(valid=False, error="invalid_checksum")

        seventh = digits[6]
        if 1 <= seventh <= 6:
            return cls.validate_iin(number, digits)
        # Всё что не ИИН — БИН (7-я цифра 0,4,5,6,7 и другие)
        return cls.validate_bin(number, digits)

    @classmethod
    def validate_iin(cls, number: str, digits: list) -> ValidationResult:
        """Валидирует ИИН, извлекает дату рождения и пол."""
        seventh = digits[6]
        yy = int(number[0:2])
        month = int(number[2:4])
        day = int(number[4:6])

        if seventh in (1, 2):
            year = 1800 + yy
        elif seventh in (3, 4):
            year = 1900 + yy
        else:
            year = 2000 + yy

        try:
            birthdate = date(year, month, day)
        except ValueError:
            return ValidationResult(valid=False, error="invalid_birthdate")

        # Пол: нечётная 7-я цифра = мужской, чётная = женский
        gender = "мужской" if seventh % 2 == 1 else "женский"

        return ValidationResult(
            valid=True,
            type="IIN",
            value=number,
            metadata={
                "birthdate": birthdate.strftime("%d.%m.%Y"),
                "gender": gender,
            },
        )

    @classmethod
    def validate_bin(cls, number: str, digits: list) -> ValidationResult:
        """Валидирует БИН, извлекает дату регистрации."""
        yy = int(number[0:2])
        month = int(number[2:4])
        day = int(number[4:6])
        year = 2000 + yy

        try:
            reg_date = date(year, month, day)
            reg_date_str = reg_date.strftime("%d.%m.%Y")
        except ValueError:
            # Некоторые БИН госорганов и НКО имеют нестандартную дату — принимаем как валидный
            reg_date_str = None

        return ValidationResult(
            valid=True,
            type="BIN",
            value=number,
            metadata={
                "registration_date": reg_date_str,
            },
        )

    # ── Телефон ───────────────────────────────────────────────────────────────

    @classmethod
    def validate_phone(cls, raw: str) -> ValidationResult:
        """
        Нормализует казахстанский номер к формату +7XXXXXXXXXX.
        Определяет тип: mobile / landline.
        """
        digits = re.sub(r'\D', '', raw.strip())

        # Приводим к 11-значному номеру, начинающемуся с 7
        if len(digits) == 11 and digits[0] in ('7', '8'):
            normalized = '7' + digits[1:]
        elif len(digits) == 10:
            normalized = '7' + digits
        else:
            return ValidationResult(valid=False, error="invalid_phone_format")

        if len(normalized) != 11 or not normalized.isdigit():
            return ValidationResult(valid=False, error="invalid_phone_format")

        phone = '+' + normalized
        prefix4 = normalized[:4]
        phone_type = "mobile" if prefix4 in _MOBILE_PREFIXES else "landline"

        return ValidationResult(
            valid=True,
            type=phone_type,
            value=phone,
            metadata={"raw": raw.strip()},
        )

    # ── Вспомогательные ───────────────────────────────────────────────────────

    @staticmethod
    def _check_control(digits: list) -> bool:
        weights1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        s = sum(digits[i] * weights1[i] for i in range(11))
        r = s % 11
        if r < 10:
            return r == digits[11]
        weights2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]
        s = sum(digits[i] * weights2[i] for i in range(11))
        r = s % 11
        if r == 10:
            r = 0
        return r == digits[11]


# ── Сообщения об ошибках (используются в forms.py и views.py) ─────────────────

IIN_BIN_ERRORS = {
    "invalid_format": "ИИН/БИН должен содержать 12 цифр.",
    "invalid_checksum": "Неверная контрольная сумма ИИН/БИН.",
    "invalid_birthdate": "Некорректная дата рождения в ИИН.",
    "invalid_registration_date": "Некорректная дата регистрации в БИН.",
    "unknown_type": "Не удалось определить тип ИИН/БИН.",
}

PHONE_ERRORS = {
    "invalid_phone_format": "Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX.",
}


# ── Обратная совместимость с предыдущим API ────────────────────────────────────

def validate_iin_bin(number: str):
    """Обёртка для обратной совместимости. Возвращает (bool, str)."""
    result = KZValidator.validate_iin_bin(number)
    if result.valid:
        return True, result.type
    return False, result.error
