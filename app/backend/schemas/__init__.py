"""Public schema package for API, tool, automation, script, settings, worker, docs, and platform domains."""

from __future__ import annotations

from . import apis as _apis
from . import automation as _automation
from . import docs as _docs
from . import platform as _platform
from . import scripts as _scripts
from . import settings as _settings
from . import tools as _tools
from . import workers as _workers
from .apis import *
from .automation import *
from .docs import *
from .platform import *
from .scripts import *
from .settings import *
from .tools import *
from .workers import *

__all__ = [
    *_apis.__all__,
    *_automation.__all__,
    *_docs.__all__,
    *_platform.__all__,
    *_scripts.__all__,
    *_settings.__all__,
    *_tools.__all__,
    *_workers.__all__,
]
