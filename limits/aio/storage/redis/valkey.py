from __future__ import annotations

from .redispy import RedispyBridge


class ValkeyBridge(RedispyBridge):
    @property
    def base_exceptions(self) -> type[Exception] | tuple[type[Exception], ...]:
        return (self.dependency.ValkeyError,)
