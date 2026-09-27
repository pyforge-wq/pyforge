from __future__ import annotations

import os
import time

_CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_ulid() -> str:
    """A 26-character Crockford-base32 ULID: a 48-bit millisecond timestamp
    followed by 80 bits of randomness (https://github.com/ulid/spec) — used
    as the default primary key type for :class:`pyforge.orm.ULIDModel`.
    Implemented in-house since the spec is small and stable enough that a
    dependency for it would be pure overhead.
    """
    timestamp_ms = int(time.time() * 1000)
    randomness = int.from_bytes(os.urandom(10), "big")
    value = (timestamp_ms << 80) | randomness

    characters = [""] * 26
    for i in range(25, -1, -1):
        characters[i] = _CROCKFORD_ALPHABET[value & 0x1F]
        value >>= 5
    return "".join(characters)
