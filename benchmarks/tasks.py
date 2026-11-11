"""Synthetic repair tasks and evaluator for the Daisychain pilot benchmark.

Only materialize() output belongs in an agent workspace. Reference solutions and
held-out checks are evaluator fixtures, not input to either experimental arm.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap


def _source(text: str) -> str:
    return textwrap.dedent(text).lstrip()


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    brief: str
    starting_source: str
    public_tests: str
    reference_source: str


TASKS: dict[str, Task] = {
    "ttl_cache": Task(
        id="ttl_cache",
        title="Repair a bounded TTL/LRU cache",
        brief=_source('''
            Repair solution.py, preserving the public TTLCache API:
            TTLCache(capacity, clock), set(key, value, ttl), get(key, default=None),
            and len(cache). clock is an injected callable returning seconds.

            Requirements:
            - capacity is a positive integer; reject bool, non-integer, zero,
              and negative capacities with ValueError.
            - Entries expire exactly when clock() >= insertion_time + ttl.
              len(), get(), and set() must discard expired entries.
            - ttl is a finite nonnegative int or float (bool is invalid).
              Invalid ttl raises ValueError without changing cache contents or
              recency. Validate ttl before performing cleanup. ttl=0 removes an
              existing value for that key and stores nothing.
            - set() of an existing key replaces its value and deadline and makes
              it most recently used. A successful get() also makes a key most
              recently used. A miss returns default and changes no live recency.
            - After removing expired entries, inserting beyond capacity evicts
              the least recently used live entry. Replacing a key must not evict
              any other key. Values may be any object, including None, 0, False,
              and empty strings; return the stored value unchanged.
            - Clock values in this task are finite and nondecreasing, and keys
              are hashable. No threads, background cleanup, or real-time waits
              are required. Do not change the public tests.

            Run the public smoke tests with: python -m unittest test_public -v
        '''),
        starting_source=_source('''
            class TTLCache:
                def __init__(self, capacity, clock):
                    self.capacity = capacity
                    self.clock = clock
                    self.items = {}

                def set(self, key, value, ttl):
                    if len(self.items) >= self.capacity:
                        self.items.pop(next(iter(self.items)))
                    self.items[key] = (value, self.clock() + ttl)

                def get(self, key, default=None):
                    item = self.items.get(key)
                    if item is None or self.clock() > item[1]:
                        return default
                    return item[0] or default

                def __len__(self):
                    return len(self.items)
        '''),
        public_tests=_source('''
            import unittest
            from solution import TTLCache

            class PublicTests(unittest.TestCase):
                def test_basic_expiry(self):
                    now = [10]
                    cache = TTLCache(2, lambda: now[0])
                    cache.set("a", "hello", 5)
                    self.assertEqual(cache.get("a"), "hello")
                    now[0] = 16
                    self.assertEqual(cache.get("a", "missing"), "missing")

                def test_capacity(self):
                    cache = TTLCache(1, lambda: 0)
                    cache.set("a", 1, 10)
                    cache.set("b", 2, 10)
                    self.assertIsNone(cache.get("a"))
                    self.assertEqual(cache.get("b"), 2)

            if __name__ == "__main__":
                unittest.main()
        '''),
        reference_source=_source('''
            from collections import OrderedDict
            import math

            class TTLCache:
                def __init__(self, capacity, clock):
                    if type(capacity) is not int or capacity <= 0:
                        raise ValueError("capacity must be a positive integer")
                    self.capacity = capacity
                    self.clock = clock
                    self.items = OrderedDict()

                def _purge(self, now):
                    for key in list(self.items):
                        if now >= self.items[key][1]:
                            del self.items[key]

                def set(self, key, value, ttl):
                    if type(ttl) not in (int, float) or not math.isfinite(ttl) or ttl < 0:
                        raise ValueError("ttl must be finite and nonnegative")
                    now = self.clock()
                    self._purge(now)
                    self.items.pop(key, None)
                    if ttl == 0:
                        return
                    self.items[key] = (value, now + ttl)
                    while len(self.items) > self.capacity:
                        self.items.popitem(last=False)

                def get(self, key, default=None):
                    self._purge(self.clock())
                    if key not in self.items:
                        return default
                    self.items.move_to_end(key)
                    return self.items[key][0]

                def __len__(self):
                    self._purge(self.clock())
                    return len(self.items)
        '''),
    ),
    "query_patch": Task(
        id="query_patch",
        title="Repair ordered URL query updates",
        brief=_source('''
            Repair patch_query(url, updates) in solution.py. url is a string;
            updates is an iterable of (key, value) pairs. Keys are strings and
            values are strings or None. Inputs are valid for urllib.parse.

            Requirements:
            - Preserve scheme, authority, path, and fragment exactly as the
              urllib.parse split/recombine representation permits. A URL may be
              relative. Query serialization may normalize percent encoding.
            - Parse query pairs with blank values retained. Unaffected repeated
              keys and their relative ordering must survive.
            - Apply updates from left to right. Each operation removes ALL
              existing pairs with that decoded key. If its value is not None,
              append exactly one pair at the end; None means delete only.
            - An empty string is a value, not a deletion. Match keys case
              sensitively after URL decoding. Values are literal text, not
              pre-encoded query fragments. Encode Unicode, spaces, ampersands,
              literal plus signs, percent signs, and equals signs correctly.
            - Do not mutate the updates input, and support a one-pass generator.
              Empty updates retain every original pair, including duplicates
              and blanks. No external requests or additional dependencies.

            Run the public smoke tests with: python -m unittest test_public -v
        '''),
        starting_source=_source('''
            from urllib.parse import urlsplit, urlunsplit, parse_qsl

            def patch_query(url, updates):
                parts = urlsplit(url)
                values = dict(parse_qsl(parts.query))
                for key, value in updates:
                    if value:
                        values[key] = value
                    else:
                        values.pop(key, None)
                query = "&".join(f"{k}={v}" for k, v in values.items())
                return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))
        '''),
        public_tests=_source('''
            import unittest
            from urllib.parse import parse_qsl, urlsplit
            from solution import patch_query

            class PublicTests(unittest.TestCase):
                def test_replace(self):
                    result = patch_query("https://example.invalid/items?a=1", [("a", "2")])
                    self.assertEqual(parse_qsl(urlsplit(result).query), [("a", "2")])

                def test_delete(self):
                    result = patch_query("/items?a=1&b=2", [("a", None)])
                    self.assertEqual(parse_qsl(urlsplit(result).query), [("b", "2")])

            if __name__ == "__main__":
                unittest.main()
        '''),
        reference_source=_source('''
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

            def patch_query(url, updates):
                parts = urlsplit(url)
                pairs = parse_qsl(parts.query, keep_blank_values=True)
                for key, value in updates:
                    pairs = [(k, v) for k, v in pairs if k != key]
                    if value is not None:
                        pairs.append((key, value))
                return urlunsplit(parts._replace(query=urlencode(pairs)))
        '''),
    ),
    "event_reconcile": Task(
        id="event_reconcile",
        title="Repair versioned events with tombstones",
        brief=_source('''
            Repair reconcile(events) in solution.py. events is a one-pass
            iterable of event dictionaries. Return a dictionary mapping each
            surviving entity identifier to its winning payload.

            Requirements:
            - Each event has entity (a nonempty string), version (a nonnegative
              integer, excluding bool), and optional deleted (a bool, default
              False). A live event must contain payload; its value can be any
              Python object including None or falsy/nested values. A tombstone
              may omit payload. Additional fields are ignored.
            - Validate EVERY event, including stale events that cannot win.
              Invalid events, missing required fields, and non-dictionary events
              raise ValueError. Whitespace is allowed in a nonempty entity and
              entity identifiers are case sensitive; do not normalize them.
            - Highest version wins per entity. If versions tie, the later input
              event wins. Input order need not be sorted by version.
            - A winning deleted=True event removes that entity from the result.
              Its version must still prevent an older live event from reviving
              the entity. A strictly newer live event can revive it.
            - Do not mutate input events. Deep-copy winning live payloads so
              later changes to nested input values do not change the result,
              and changing the result does not change the inputs.
            - Empty input returns {}. No external storage or dependencies.

            Run the public smoke tests with: python -m unittest test_public -v
        '''),
        starting_source=_source('''
            def reconcile(events):
                result = {}
                versions = {}
                for event in events:
                    entity = event["entity"]
                    version = event["version"]
                    if event.get("deleted"):
                        result.pop(entity, None)
                        versions.pop(entity, None)
                    elif version > versions.get(entity, -1):
                        versions[entity] = version
                        result[entity] = event["payload"]
                return result
        '''),
        public_tests=_source('''
            import unittest
            from solution import reconcile

            class PublicTests(unittest.TestCase):
                def test_largest_version(self):
                    events = [
                        {"entity": "a", "version": 2, "payload": "new"},
                        {"entity": "a", "version": 1, "payload": "old"},
                    ]
                    self.assertEqual(reconcile(events), {"a": "new"})

                def test_delete(self):
                    events = [
                        {"entity": "a", "version": 1, "payload": "old"},
                        {"entity": "a", "version": 2, "deleted": True},
                    ]
                    self.assertEqual(reconcile(events), {})

            if __name__ == "__main__":
                unittest.main()
        '''),
        reference_source=_source('''
            from copy import deepcopy

            def reconcile(events):
                winners = {}
                for event in events:
                    if not isinstance(event, dict):
                        raise ValueError("event must be a dictionary")
                    entity = event.get("entity")
                    version = event.get("version")
                    deleted = event.get("deleted", False)
                    if not isinstance(entity, str) or not entity:
                        raise ValueError("entity must be a nonempty string")
                    if type(version) is not int or version < 0:
                        raise ValueError("version must be a nonnegative integer")
                    if type(deleted) is not bool:
                        raise ValueError("deleted must be boolean")
                    if not deleted and "payload" not in event:
                        raise ValueError("live event requires payload")
                    if entity not in winners or version >= winners[entity]["version"]:
                        winners[entity] = event
                return {key: deepcopy(event["payload"])
                        for key, event in winners.items()
                        if not event.get("deleted", False)}
        '''),
    ),
    "csv_import": Task(
        id="csv_import",
        title="Repair a strict typed CSV importer",
        brief=_source('''
            Repair load_people(text) in solution.py. Return a list of dictionaries
            with keys name (str), email (str), age (int or None), active (bool).

            Requirements:
            - Parse standard comma-separated CSV, including quoted commas and
              embedded newlines. Allow one UTF-8 BOM character at the very start.
              Malformed CSV quoting must raise ValueError.
            - The first CSV record is the header. Strip header whitespace; it
              must contain exactly name, email, age, active in any order, with
              no duplicates or additional columns. Missing/empty input is invalid.
            - Ignore data rows whose every field is blank after stripping.
              Every other row must have exactly as many fields as the header.
            - Strip surrounding whitespace from all values. name is required.
              email is required, lowercased, and must have exactly one @, with
              nonempty local/domain parts and no whitespace anywhere. No other
              email syntax or deliverability validation is required.
            - Empty age becomes None; otherwise allow only ASCII decimal digits
              and require 0 <= age <= 130. Reject signs, fractions, and Unicode
              digit characters.
            - active is case insensitive: true or 1 gives True; false, 0, or an
              empty value gives False. Reject all other values.
            - Return data in input order. Any invalid nonblank record raises
              ValueError rather than returning partial results. No external
              network requests or dependencies. Do not change public tests.

            Run the public smoke tests with: python -m unittest test_public -v
        '''),
        starting_source=_source('''
            def load_people(text):
                lines = text.strip().splitlines()
                header = lines[0].split(",")
                result = []
                for line in lines[1:]:
                    row = dict(zip(header, line.split(",")))
                    result.append({
                        "name": row["name"],
                        "email": row["email"],
                        "age": int(row["age"]) if row["age"] else None,
                        "active": bool(row["active"]),
                    })
                return result
        '''),
        public_tests=_source('''
            import unittest
            from solution import load_people

            class PublicTests(unittest.TestCase):
                def test_basic(self):
                    result = load_people("name,email,age,active\\nSam,sam@example.invalid,30,true\\n")
                    self.assertEqual(result, [{"name": "Sam", "email": "sam@example.invalid", "age": 30, "active": True}])

                def test_blank_age(self):
                    result = load_people("name,email,age,active\\nJo,jo@example.invalid,,1\\n")
                    self.assertIsNone(result[0]["age"])

            if __name__ == "__main__":
                unittest.main()
        '''),
        reference_source=_source('''
            import csv
            import io

            def load_people(text):
                if text.startswith("\\ufeff"):
                    text = text[1:]
                try:
                    records = iter(csv.reader(io.StringIO(text, newline=""), strict=True))
                    header = [cell.strip() for cell in next(records)]
                    if len(header) != 4 or set(header) != {"name", "email", "age", "active"}:
                        raise ValueError("invalid header")
                    result = []
                    for record in records:
                        if not any(cell.strip() for cell in record):
                            continue
                        if len(record) != len(header):
                            raise ValueError("invalid row width")
                        row = dict(zip(header, (cell.strip() for cell in record)))
                        name, email = row["name"], row["email"].lower()
                        if not name or email.count("@") != 1 or any(c.isspace() for c in email):
                            raise ValueError("invalid name or email")
                        if not all(email.split("@")):
                            raise ValueError("invalid email")
                        age = row["age"]
                        if age and (not age.isascii() or not age.isdecimal()):
                            raise ValueError("invalid age")
                        age = int(age) if age else None
                        if age is not None and not 0 <= age <= 130:
                            raise ValueError("age outside range")
                        active = row["active"].lower()
                        if active not in ("true", "1", "false", "0", ""):
                            raise ValueError("invalid active")
                        result.append({"name": name, "email": email, "age": age,
                                       "active": active in ("true", "1")})
                    return result
                except (csv.Error, StopIteration) as exc:
                    raise ValueError("invalid CSV") from exc
        '''),
    ),
}


# These checks are deliberately not written by materialize(). All requirements
# they exercise are present in each task brief; hidden here means held out from
# the agent workspace, not a claim of secure secrecy on a shared host.
_CHECKS: dict[str, list[tuple[str, str]]] = {
    "ttl_cache": [
        ("expiry_boundary", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,5); c.now=5; eq(x.get("a","miss"),"miss"); eq(len(x),0)'),
        ("falsy_values", 'c=Clock(); x=m.TTLCache(5,c); vals=[None,0,False,"",[]]; [x.set(i,v,5) for i,v in enumerate(vals)]; [eq(x.get(i,"miss"),v) for i,v in enumerate(vals)]'),
        ("get_refreshes_lru", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,10); x.get("a"); x.set("c",3,10); eq(x.get("b","miss"),"miss"); eq(x.get("a"),1)'),
        ("replace_without_eviction", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,10); x.set("b",20,20); eq(x.get("a"),1); eq(x.get("b"),20); eq(len(x),2)'),
        ("replace_refreshes_lru", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,10); x.set("a",10,10); x.set("c",3,10); eq(x.get("b","miss"),"miss"); eq(x.get("a"),10)'),
        ("expired_entries_before_eviction", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,1); c.now=2; x.set("c",3,10); eq(x.get("a"),1); eq(x.get("c"),3); eq(len(x),2)'),
        ("len_purges_expired", 'c=Clock(); x=m.TTLCache(3,c); x.set("a",1,1); x.set("b",2,5); c.now=1; eq(len(x),1); c.now=5; eq(len(x),0)'),
        ("zero_ttl_removes", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,5); x.set("b",2,5); x.set("a",9,0); eq(len(x),1); eq(x.get("a","miss"),"miss"); eq(x.get("b"),2)'),
        ("zero_new_key_does_not_evict", 'c=Clock(); x=m.TTLCache(1,c); x.set("a",1,5); x.set("b",2,0); eq(x.get("a"),1); eq(len(x),1)'),
        ("invalid_capacity", '[raises(ValueError,m.TTLCache,v,Clock()) for v in [0,-1,True,1.5,"2",None]]'),
        ("invalid_ttl_no_mutation", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,10); [raises(ValueError,x.set,"a",99,v) for v in [-1,float("nan"),float("inf"),True,"3",None]]; x.set("c",3,10); eq(x.get("a","miss"),"miss"); eq(x.get("b"),2)'),
        ("invalid_ttl_preserves_value", 'c=Clock(); x=m.TTLCache(1,c); x.set("a",{"value":1},10); raises(ValueError,x.set,"a",{"value":99},-1); eq(x.get("a"),{"value":1}); eq(len(x),1)'),
        ("replacement_deadline", 'c=Clock(); x=m.TTLCache(1,c); x.set("a",1,1); c.now=.5; x.set("a",2,4); c.now=1; eq(x.get("a"),2); c.now=4.5; eq(x.get("a","miss"),"miss")'),
        ("miss_preserves_recency", 'c=Clock(); x=m.TTLCache(2,c); x.set("a",1,10); x.set("b",2,10); sentinel=object(); eq(x.get("missing",sentinel) is sentinel,True); x.set("c",3,10); eq(x.get("a","miss"),"miss"); eq(x.get("b"),2)'),
    ],
    "query_patch": [
        ("unaffected_duplicates", 'eq(pairs(m.patch_query("/p?a=1&a=2&z=3",[("z","4")])),[("a","1"),("a","2"),("z","4")])'),
        ("blank_values_retained", 'eq(pairs(m.patch_query("/p?a=&b&c=3",[])),[("a",""),("b",""),("c","3")])'),
        ("empty_is_not_delete", 'eq(pairs(m.patch_query("/p?a=1&b=2",[("a","")])),[("b","2"),("a","")])'),
        ("remove_all_matching_pairs", 'eq(pairs(m.patch_query("/p?a=1&b=2&a=3",[("a",None)])),[("b","2")])'),
        ("replacement_appended", 'eq(pairs(m.patch_query("/p?a=1&b=2&c=3",[("b","4")])),[("a","1"),("c","3"),("b","4")])'),
        ("sequential_repeated_updates", 'eq(pairs(m.patch_query("/p?a=1&b=2",[("a","3"),("b",None),("a","4"),("b","")])),[("a","4"),("b","")])'),
        ("preserve_url_components", 'from urllib.parse import urlsplit; u="https://user:pass@example.invalid:8443/a%2Fb?x=1#frag?keep"; a=urlsplit(u); b=urlsplit(m.patch_query(u,[("y","2")])); eq((b.scheme,b.netloc,b.path,b.fragment),(a.scheme,a.netloc,a.path,a.fragment))'),
        ("relative_url_fragment", 'from urllib.parse import urlsplit; u=m.patch_query("../items#section",[("x","1")]); p=urlsplit(u); eq((p.scheme,p.netloc,p.path,p.fragment),("","","../items","section")); eq(pairs(u),[("x","1")])'),
        ("literal_special_characters", 'v="x + y&z=100%"; eq(pairs(m.patch_query("/p",[("a&=+",v)])),[("a&=+",v)])'),
        ("unicode_roundtrip", 'eq(pairs(m.patch_query("/p",[("café","雪 ☃")])),[("café","雪 ☃")])'),
        ("decoded_key_matching", 'eq(pairs(m.patch_query("/p?a%20b=1&a+b=2&A+b=3",[("a b","new")])),[("A b","3"),("a b","new")])'),
        ("generator_updates", 'eq(pairs(m.patch_query("/p?z=0",((k,v) for k,v in [("a","1"),("z",None)]))),[("a","1")])'),
        ("input_not_mutated", 'u=[["a","1"],["b",None]]; original=[x[:] for x in u]; m.patch_query("/p?b=2",u); eq(u,original)'),
        ("delete_absent_and_empty_key", 'eq(pairs(m.patch_query("/p?=blank&a=1",[("missing",None),("","new")])),[("a","1"),("","new")])'),
    ],
    "event_reconcile": [
        ("highest_version_unsorted", 'eq(m.reconcile([{"entity":"a","version":3,"payload":"new"},{"entity":"a","version":1,"payload":"old"}]),{"a":"new"})'),
        ("later_tie_wins", 'eq(m.reconcile([{"entity":"a","version":2,"payload":"first"},{"entity":"a","version":2,"payload":"last"}]),{"a":"last"})'),
        ("tombstone_blocks_stale_revival", 'eq(m.reconcile([{"entity":"a","version":5,"deleted":True},{"entity":"a","version":4,"payload":"old"}]),{})'),
        ("stale_tombstone_ignored", 'eq(m.reconcile([{"entity":"a","version":5,"payload":"new"},{"entity":"a","version":4,"deleted":True}]),{"a":"new"})'),
        ("newer_live_revives", 'eq(m.reconcile([{"entity":"a","version":1,"deleted":True},{"entity":"a","version":2,"payload":"back"}]),{"a":"back"})'),
        ("tied_delete_then_live", 'eq(m.reconcile([{"entity":"a","version":2,"deleted":True},{"entity":"a","version":2,"payload":None}]),{"a":None})'),
        ("tied_live_then_delete", 'eq(m.reconcile([{"entity":"a","version":2,"payload":1},{"entity":"a","version":2,"deleted":True}]),{})'),
        ("falsy_payloads_and_zero_version", 'eq(m.reconcile([{"entity":str(i),"version":0,"payload":v} for i,v in enumerate([0,False,None,"",[]])]),{str(i):v for i,v in enumerate([0,False,None,"",[]])})'),
        ("generator_and_empty", 'eq(m.reconcile(iter([])),{}); eq(m.reconcile(iter([{"entity":"a","version":1,"payload":2}])),{"a":2})'),
        ("invalid_entity", '[raises(ValueError,m.reconcile,[{"entity":v,"version":1,"payload":1}]) for v in ["",None,1,False]]'),
        ("invalid_version", '[raises(ValueError,m.reconcile,[{"entity":"a","version":v,"payload":1}]) for v in [-1,True,1.0,"1",None]]'),
        ("invalid_deleted", '[raises(ValueError,m.reconcile,[{"entity":"a","version":1,"deleted":v,"payload":1}]) for v in [None,0,1,"false"]]'),
        ("missing_fields_and_wrong_type", '[raises(ValueError,m.reconcile,[v]) for v in [None,[],{}, {"version":1,"payload":1},{"entity":"a","payload":1},{"entity":"a","version":1}]]'),
        ("validate_stale_events", 'raises(ValueError,m.reconcile,[{"entity":"a","version":5,"payload":"good"},{"entity":"a","version":1}])'),
        ("deep_copy_and_input_unchanged", 'from copy import deepcopy; events=[{"entity":"a","version":1,"payload":{"items":[1]}}]; before=deepcopy(events); r=m.reconcile(events); eq(events,before); r["a"]["items"].append(2); eq(events,before); events[0]["payload"]["items"].append(3); eq(r,{"a":{"items":[1,2]}})'),
        ("entity_not_normalized", 'eq(m.reconcile([{"entity":" a ","version":1,"payload":1},{"entity":"A","version":1,"payload":2},{"entity":"a","version":1,"payload":3}]),{" a ":1,"A":2,"a":3})'),
    ],
    "csv_import": [
        ("trim_and_reorder_header", 'eq(m.load_people(" active , age , email , name \\n FALSE , 0 , SAM@EXAMPLE.INVALID , Sam \\n"),[{"name":"Sam","email":"sam@example.invalid","age":0,"active":False}])'),
        ("quoted_commas_and_newlines", 'eq(m.load_people(\'name,email,age,active\\n"Sam, Jr.\\nII",sam@example.invalid,30,true\\n\'),[{"name":"Sam, Jr.\\nII","email":"sam@example.invalid","age":30,"active":True}])'),
        ("bom_and_crlf", 'eq(m.load_people("\\ufeffname,email,age,active\\r\\nSam,sam@example.invalid,130,0\\r\\n")[0]["age"],130); eq(m.load_people("\\ufeffname,email,age,active\\r\\nSam,sam@example.invalid,130,0\\r\\n")[0]["active"],False)'),
        ("blank_rows_and_age", 'eq(m.load_people("name,email,age,active\\n\\n,,,\\nSam,sam@example.invalid,,\\n"),[{"name":"Sam","email":"sam@example.invalid","age":None,"active":False}])'),
        ("active_tokens", '[eq(m.load_people("name,email,age,active\\nSam,sam@example.invalid,20,"+token+"\\n")[0]["active"],expected) for token,expected in [("true",True),("TrUe",True),("1",True),("false",False),("FALSE",False),("0",False),("",False)]]'),
        ("invalid_active", '[raises(ValueError,m.load_people,"name,email,age,active\\nSam,sam@example.invalid,20,"+token+"\\n") for token in ["yes","no","2","null"]]'),
        ("invalid_age_syntax", '[raises(ValueError,m.load_people,"name,email,age,active\\nSam,sam@example.invalid,"+token+",true\\n") for token in ["-1","+1","1.5","١٢","１２","abc"]]'),
        ("age_boundaries", 'eq(m.load_people("name,email,age,active\\nSam,sam@example.invalid,000,true\\n")[0]["age"],0); raises(ValueError,m.load_people,"name,email,age,active\\nSam,sam@example.invalid,131,true\\n")'),
        ("invalid_email", '[raises(ValueError,m.load_people,"name,email,age,active\\nSam,"+email+",20,true\\n") for email in ["","sam","@example.invalid","sam@","sam@@example.invalid","sa m@example.invalid"]]'),
        ("email_minimal_syntax", 'eq(m.load_people("name,email,age,active\\nSam,A@B,20,true\\n")[0]["email"],"a@b")'),
        ("name_required", 'raises(ValueError,m.load_people,"name,email,age,active\\n ,sam@example.invalid,20,true\\n")'),
        ("invalid_headers", '[raises(ValueError,m.load_people,text) for text in ["","\\n","name,email,age\\n","name,email,age,active,extra\\n","name,email,age,name\\n","Name,email,age,active\\n"]]'),
        ("row_width", '[raises(ValueError,m.load_people,"name,email,age,active\\n"+row+"\\n") for row in ["Sam,sam@example.invalid,20","Sam,sam@example.invalid,20,true,extra"]]'),
        ("invalid_later_row_no_partial_return", 'raises(ValueError,m.load_people,"name,email,age,active\\nSam,sam@example.invalid,20,true\\nJo,jo@example.invalid,bad,true\\n")'),
        ("header_only_and_order", 'eq(m.load_people("name,email,age,active\\n"),[]); r=m.load_people("name,email,age,active\\nZed,z@example.invalid,1,true\\nAmy,a@example.invalid,2,false\\n"); eq([x["name"] for x in r],["Zed","Amy"])'),
        ("malformed_quoting", 'raises(ValueError,m.load_people,\'name,email,age,active\\n"Sam,sam@example.invalid,20,true\\n\')'),
    ],
}


def materialize(task_id: str, directory: str | Path) -> Path:
    """Write only the brief, starting solution, and public tests to a workspace."""
    task = TASKS[task_id]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "TASK.md").write_text(task.brief, encoding="utf-8")
    (directory / "solution.py").write_text(task.starting_source, encoding="utf-8")
    (directory / "test_public.py").write_text(task.public_tests, encoding="utf-8")
    return directory


_WORKER = r'''
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import parse_qsl, urlsplit

class Clock:
    def __init__(self):
        self.now = 0
    def __call__(self):
        return self.now

def eq(actual, expected):
    if actual != expected:
        raise AssertionError(f"expected {expected!r}; got {actual!r}")

def raises(kind, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except kind:
        return
    except BaseException as exc:
        raise AssertionError(f"expected {kind.__name__}; got {type(exc).__name__}") from exc
    raise AssertionError(f"expected {kind.__name__}; no exception raised")

def pairs(url):
    return parse_qsl(urlsplit(url).query, keep_blank_values=True)

payload = json.loads(sys.stdin.read())
results = []
for index, (name, code) in enumerate(payload["checks"]):
    try:
        module_name = f"candidate_{index}"
        spec = importlib.util.spec_from_file_location(module_name, payload["solution_path"])
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        exec(code, {"m": module, "eq": eq, "raises": raises, "Clock": Clock, "pairs": pairs})
        results.append({"name": name, "passed": True})
    except BaseException as exc:
        results.append({"name": name, "passed": False,
                        "error": f"{type(exc).__name__}: {exc}"[:1000]})
print("DAISYCHAIN_RESULT=" + json.dumps(results, ensure_ascii=True))
'''


_PUBLIC_WORKER = r'''
import json
import sys
import unittest

sys.path.insert(0, sys.argv[1])
suite = unittest.defaultTestLoader.loadTestsFromName("test_public")
result = unittest.TextTestRunner(verbosity=1).run(suite)
print("DAISYCHAIN_PUBLIC_RESULT=" + json.dumps({
    "passed": result.wasSuccessful() and result.testsRun > 0,
    "tests_run": result.testsRun,
}))
sys.exit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
'''


def evaluate(task_id: str, solution_path: str | Path, timeout: float = 10) -> dict:
    """Run held-out checks in an isolated Python subprocess with a time limit.

    This is a resource bound and environment cleanup, not a security sandbox for
    hostile code. Use an external sandbox when evaluating untrusted submissions.
    """
    checks = _CHECKS[task_id]
    solution_path = Path(solution_path).resolve()
    payload = json.dumps({"solution_path": str(solution_path), "checks": checks})
    public_pass = False
    public_run = 0
    public_error = None
    with tempfile.TemporaryDirectory(prefix="daisychain-evaluator-") as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _WORKER],
                input=payload, text=True, capture_output=True, timeout=timeout,
                cwd=tmp, env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            outputs = [line for line in proc.stdout.splitlines() if line.startswith("DAISYCHAIN_RESULT=")]
            if proc.returncode != 0 or not outputs:
                raise RuntimeError(f"evaluator exited {proc.returncode}: {proc.stderr[-1000:]}")
            results = json.loads(outputs[-1].split("=", 1)[1])
        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as exc:
            results = [{"name": name, "passed": False,
                        "error": f"{type(exc).__name__}: {exc}"[:1000]} for name, _ in checks]
        try:
            public_root = Path(tmp) / "public"
            public_root.mkdir()
            (public_root / "solution.py").write_text(solution_path.read_text(encoding="utf-8"), encoding="utf-8")
            (public_root / "test_public.py").write_text(TASKS[task_id].public_tests, encoding="utf-8")
            public_proc = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _PUBLIC_WORKER, str(public_root)],
                text=True, capture_output=True, timeout=timeout,
                cwd=public_root, env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"},
                check=False,
            )
            outputs = [line for line in public_proc.stdout.splitlines()
                       if line.startswith("DAISYCHAIN_PUBLIC_RESULT=")]
            if not outputs:
                raise RuntimeError(f"public evaluator exited {public_proc.returncode}: {public_proc.stderr[-1000:]}")
            public_result = json.loads(outputs[-1].split("=", 1)[1])
            public_run = public_result["tests_run"]
            public_pass = public_proc.returncode == 0 and public_result["passed"]
            if not public_pass:
                public_error = public_proc.stderr[-1000:]
        except (OSError, UnicodeError, subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as exc:
            public_error = f"{type(exc).__name__}: {exc}"[:1000]
    passed = sum(item["passed"] for item in results)
    return {"task_id": task_id, "task_pass": passed == len(checks) and public_pass,
            "passed": passed, "total": len(checks), "checks": results,
            "public_tests_pass": public_pass, "public_tests_run": public_run,
            "public_tests_error": public_error}
