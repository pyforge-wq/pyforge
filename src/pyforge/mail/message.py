from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    to: list[str]
    from_address: str
    subject: str
    html: str | None = None
    text: str | None = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
