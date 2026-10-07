import csv
import os
import config

def save(kind, rows):
    if not rows:
        return

    month = rows[0]["run_time_ist"][:7]  
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, f"{kind}_{month}.csv")

    columns = list(rows[0].keys())

    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, newline="", encoding="utf-8") as f:
            existing_columns = next(csv.reader(f))
        if existing_columns != columns:
            columns = _upgrade_file(path, existing_columns, columns)
        write_header = False
    else:
        write_header = True

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _upgrade_file(path, old_columns, new_columns):
    """
    When we add new columns later (e.g. weather), rewrite this month's file
    with the extra columns. Old rows simply get empty cells for them.
    """
    merged = old_columns + [c for c in new_columns if c not in old_columns]
    with open(path, newline="", encoding="utf-8") as f:
        old_rows = list(csv.DictReader(f))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=merged, restval="")
        writer.writeheader()
        writer.writerows(old_rows)
    return merged
