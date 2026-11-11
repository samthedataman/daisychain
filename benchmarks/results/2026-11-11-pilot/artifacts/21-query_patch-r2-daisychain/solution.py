from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

def patch_query(url, updates):
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    for key, value in updates:
        pairs = [(k, v) for k, v in pairs if k != key]
        if value is not None:
            pairs.append((key, value))
    query = urlencode(pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
