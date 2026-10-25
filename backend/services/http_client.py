"""Tiny HTTP helpers on top of the standard library (no extra package needed).

External services (Nominatim, Copernicus) are called through these two functions, so tests
can replace them and never touch the internet."""
import json
import urllib.request

TIMEOUT_S = 20


def request_json(url: str, data: bytes = None, headers: dict = None, method: str = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_bytes(url: str, data: bytes = None, headers: dict = None, method: str = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()
