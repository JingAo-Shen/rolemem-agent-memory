from dateutil.parser import UnknownTimezoneWarning

def get_tz_warning_name() -> str:
    return UnknownTimezoneWarning.__name__
