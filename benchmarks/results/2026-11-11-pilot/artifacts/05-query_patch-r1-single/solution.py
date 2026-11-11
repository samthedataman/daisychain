from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def patch_query(url, updates):
    parts = urlsplit(url)
    values = parse_qsl(parts.query, keep_blank_values=True)
    for key, value in updates:
        values = [(k, v) for k, v in values if k != key]
        if value is not None:
            values.append((key, value))
    query = urlencode(values)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
