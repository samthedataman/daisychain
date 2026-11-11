from urllib.parse import parse_qsl, urlencode, urlsplit

def patch_query(url, updates):
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    for key, value in updates:
        pairs = [(k, v) for k, v in pairs if k != key]
        if value is not None:
            pairs.append((key, value))
    return parts._replace(query=urlencode(pairs)).geturl()
