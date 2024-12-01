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

class ColumnLabelSpecifiers(ConstantsGroup):
    CONSTRAINTINDICATOR = 'constraint'
    DEADLINEINDICATOR   = 'deadline'
    EFFORTINDICATOR     = 'effort'
    PRIORITYINDICATOR   = 'priority'

class TasklistColumnLabels(ConstantsGroup):
    __slots__ = ()
    TASKNUMBER     = 'Number'
    TASKNAME       = 'Name'
    TASKGROUPIDX   = 'Groupindex'

class TaskgroupColumnLabels(ConstantsGroup):
    __slots__ = ()
    GROUNAME       = 'Name'

__all__ = ("__version__", "TasklistColumnLabels", "TaskgroupColumnLabels")

