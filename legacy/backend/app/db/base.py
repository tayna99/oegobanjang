from __future__ import annotations

import sys

from sqlalchemy.orm import DeclarativeBase


if __name__ == "backend.app.db.base":
    sys.modules.setdefault("app.db.base", sys.modules[__name__])
elif __name__ == "app.db.base":
    sys.modules.setdefault("backend.app.db.base", sys.modules[__name__])


class Base(DeclarativeBase):
    pass
