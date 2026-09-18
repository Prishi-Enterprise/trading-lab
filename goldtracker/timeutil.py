from datetime import timedelta, timezone

# Fixed offset avoids a tzdata dependency (Windows / slim containers). India has no DST.
IST = timezone(timedelta(hours=5, minutes=30), "IST")


def inr(x: float) -> str:
    """Indian digit grouping: 153470 -> '1,53,470'."""
    neg = x < 0
    s = f"{abs(x):.0f}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + "₹" + s
