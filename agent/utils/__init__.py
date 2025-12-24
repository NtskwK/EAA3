from datetime import datetime


def get_format_timestamp():
    now = datetime.now()
    date = now.strftime("%Y.%m.%d")
    time = now.strftime("%H.%M.%S")
    milliseconds = f"{now.microsecond // 1000:03d}"

    return f"{date}-{time}.{milliseconds}"
