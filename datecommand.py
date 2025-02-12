# extension that parses date from the command.

from datetime import date, timedelta

# str can be 1 date or 2 dates separated by a space
# each date can be / separated day/month/year, day/month (current year), or day (current month and year)

def parse_part(part: str) -> date:
    """
    Parses a part of the date.

    Args:
        part (str): The part of the date.

    Returns:
        date: The date.
    """
    parts = part.split("/")
    if len(parts) == 3:
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    elif len(parts) == 2:
        return date(date.today().year, int(parts[1]), int(parts[0]))
    elif len(parts) == 1:
        return date(date.today().year, date.today().month, int(parts[0]))
    else:
        raise ValueError("Invalid date format")


def parse_date(cmd: str) -> tuple[date, date]:
    """
    Parses the date from the command.

    Args:
        cmd (str): The command.

    Returns:
        tuple[date, date]: The start and end dates.
    """
    today = date.today()
    dates = cmd.split()
    if len(dates) >2 or len(dates) < 1:
        raise ValueError("Invalid number of dates")
    elif len(dates) == 1:
        start = parse_part(dates[0])
        end = start  # it will internally convert to 23:59:59
    else:
        start = parse_part(dates[0])
        end = parse_part(dates[1])
    return start, end


# small test
def test():
    assert parse_part("1") == date(date.today().year, date.today().month, 1)
    assert parse_part("1/2") == date(date.today().year, 2, 1)
    assert parse_part("1/2/3") == date(3, 2, 1)
    assert parse_date("1") == (date(date.today().year, date.today().month, 1), date(date.today().year, date.today().month, 1))
    assert parse_date("1/2") == (date(date.today().year, 2, 1), date(date.today().year, 2, 1))
    assert parse_date("1 2") == (date(date.today().year, date.today().month, 1), date(date.today().year, date.today().month, 2))
    assert parse_date("1/2 3/4") == (date(date.today().year, 2, 1), date(date.today().year, 4, 3))
    assert parse_date("1/2/3 4/5/6") == (date(3, 2, 1), date(6, 5, 4))
    try:
        parse_date("1 2 3")
    except ValueError as e:
        assert str(e) == "Invalid number of dates"
    try:
        parse_date("1/2/3 4/5 6")
    except ValueError as e:
        assert str(e) == "Invalid number of dates"
    try:
        parse_date("1/2/3 4/5/6 7/8/9")
    except ValueError as e:
        assert str(e) == "Invalid number of dates"
    print("PASSED")

if __name__ == "__main__":
    test()