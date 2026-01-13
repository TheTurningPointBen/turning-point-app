from datetime import date


def billing_period_for(today: date):
    # if day <=25, billing period is 26 of previous month -> 25 of current month
    if today.day <= 25:
        # previous month
        if today.month == 1:
            prev_month = 12
            prev_year = today.year - 1
        else:
            prev_month = today.month - 1
            prev_year = today.year
        start_period = date(prev_year, prev_month, 26)
        end_period = date(today.year, today.month, 25)
    else:
        # day >25: billing period is 26 of current month -> 25 of next month
        if today.month == 12:
            next_month = 1
            next_year = today.year + 1
        else:
            next_month = today.month + 1
            next_year = today.year
        start_period = date(today.year, today.month, 26)
        end_period = date(next_year, next_month, 25)
    return start_period, end_period


test_dates = [
    date(2026, 1, 24),
    date(2026, 1, 25),
    date(2026, 1, 26),
    date(2026, 1, 27),
    date(2026, 2, 25),
    date(2026, 2, 26),
    date(2026, 12, 25),
    date(2026, 12, 26),
    date(2026, 3, 1),
    date(2026, 11, 26),
]

for d in test_dates:
    s, e = billing_period_for(d)
    print(f"Today: {d.strftime('%d %b %Y')} -> Billing period: {s.strftime('%d %b %Y')} to {e.strftime('%d %b %Y')}")
