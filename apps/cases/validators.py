import re
from datetime import datetime

NUMBER_REGEX = re.compile(r'^\d{12}$')


def validate_iin_bin(number: str):
    """
    Валидирует ИИН или БИН по казахстанскому алгоритму.
    Возвращает (True, "IIN"|"BIN") или (False, код_ошибки).
    """
    if not NUMBER_REGEX.match(number):
        return False, "invalid_format"

    digits = [int(d) for d in number]

    def check_control():
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

    if not check_control():
        return False, "invalid_checksum"

    seventh = digits[6]

    if 1 <= seventh <= 6:
        year = int(number[0:2])
        month = int(number[2:4])
        day = int(number[4:6])
        if seventh in [1, 2]:
            year += 1800
        elif seventh in [3, 4]:
            year += 1900
        else:
            year += 2000
        try:
            datetime(year, month, day)
            return True, "IIN"
        except ValueError:
            return False, "invalid_birthdate"

    elif 4 <= seventh <= 7:
        year = int(number[0:2]) + 2000
        month = int(number[2:4])
        day = int(number[4:6])
        try:
            datetime(year, month, day)
            return True, "BIN"
        except ValueError:
            return False, "invalid_registration_date"

    return False, "unknown_type"
