"""Parse and validate a synthetic people CSV."""

import csv
import io


def _validate_quotes(text):
    """Reject quotes in unquoted fields, which csv.reader permits."""
    state = "start"
    for char in text:
        if state == "quoted":
            if char == '"':
                state = "closed"
        elif state == "closed":
            if char == '"':
                state = "quoted"  # A doubled quote within a quoted field.
            elif char == ',' or char in '\r\n':
                state = "start"
            else:
                raise ValueError("Unexpected character after closing quote")
        elif char == '"':
            if state != "start":
                raise ValueError("Quote in an unquoted field")
            state = "quoted"
        elif char == ',' or char in '\r\n':
            state = "start"
        else:
            state = "unquoted"
    if state == "quoted":
        raise ValueError("Unterminated quoted field")


def load_people(text):
    if text.startswith('\ufeff'):
        text = text[1:]
    _validate_quotes(text)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    result = []
    try:
        header = next(reader, None)
        if header is None:
            raise ValueError("Missing header")
        header = [field.strip() for field in header]
        if len(header) != 4 or set(header) != {"name", "email", "age", "active"}:
            raise ValueError("Invalid header")

        for fields in reader:
            fields = [field.strip() for field in fields]
            if not any(fields):
                continue
            if len(fields) != len(header):
                raise ValueError("Invalid row width")
            row = dict(zip(header, fields))
            name = row["name"]
            email = row["email"].lower()
            if not name:
                raise ValueError("Missing name")
            if (email.count('@') != 1 or any(c.isspace() for c in email)
                    or not all(email.split('@'))):
                raise ValueError("Invalid email")

            age_text = row["age"]
            age = None
            if age_text:
                if any(c not in '0123456789' for c in age_text):
                    raise ValueError("Invalid age")
                # Bound conversion size even for arbitrarily long input.
                significant = age_text.lstrip('0') or '0'
                if len(significant) > 3 or int(significant) > 130:
                    raise ValueError("Age out of range")
                age = int(significant)

            active_text = row["active"].lower()
            if active_text not in {"true", "1", "false", "0", ""}:
                raise ValueError("Invalid active value")
            result.append({"name": name, "email": email, "age": age,
                           "active": active_text in {"true", "1"}})
    except csv.Error as exc:
        raise ValueError("Malformed CSV") from exc
    return result
