"""Client probe profiles.

We probe every endpoint with more than one client profile so we can tell
"what the server supports" apart from "what it happened to negotiate".

Each profile is just a list of key-exchange groups to offer. openssl picks
whatever the server prefers from that list.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    """A named set of groups to offer in the ClientHello."""

    name: str
    groups: list[str]


# Classical-only client: reveals the classical fallback.
CLASSICAL = Profile(
    name="classical",
    groups=["x25519", "secp256r1"],
)

# Hybrid-capable client: offers a PQ hybrid group too. If the server picks it,
# the endpoint is hybrid-capable even if a classical client would not see it.
HYBRID_CAPABLE = Profile(
    name="hybrid_capable",
    groups=["X25519MLKEM768", "x25519", "secp256r1"],
)

_BY_NAME = {p.name: p for p in (CLASSICAL, HYBRID_CAPABLE)}


def get_profile(name: str) -> Profile:
    """Look up a profile by name; raise if it is not defined."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise ValueError(f"unknown probe profile: {name!r}") from None
