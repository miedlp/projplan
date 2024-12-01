# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import importlib
import re

from .__version__ import __version__

class ConstantsGroup():
    @classmethod
    def allConstantDict(cls):
        return {name: getattr(cls, name) for name in dir(cls) if re.match('[A-Z]+[A-Z0-9_]+', name) is not None}

__all__ = ("__version__",)

