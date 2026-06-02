import datetime

def parse_date(date_str: str) -> datetime.datetime:
    return datetime.datetime.strptime(date_str, "%d.%m.%Y %H:%M")
