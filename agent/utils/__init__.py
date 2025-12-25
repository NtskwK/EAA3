from datetime import datetime


def get_format_timestamp():
    now = datetime.now()
    date = now.strftime("%Y.%m.%d")
    time = now.strftime("%H.%M.%S")
    milliseconds = f"{now.microsecond // 1000:03d}"

    return f"{date}-{time}.{milliseconds}"


def smaller(a: int | str, b: int | str) -> int:
    isDigitA = str(a).isdigit()
    isDigitB = str(b).isdigit()
    if isDigitA and isDigitB:
        return int(a) if int(a) < int(b) else int(b)
    elif not isDigitA:
        raise ValueError("Cannot compare digit with non-digit <a>")
    elif not isDigitB:
        raise ValueError("Cannot compare digit with non-digit <b>")
    else:
        raise RuntimeError("Unexpected error in smaller() function")
