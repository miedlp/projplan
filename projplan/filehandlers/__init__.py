# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

from projplan import ConstantsGroup

class InputFileStandardLabels():
    CONSTRAINTINDICATOR = '-constraint'

class MRDCSVColumnLabels(ConstantsGroup):
    __slots__ = ()
    TASKNUMBER     = 'Number'
    TASKNAME       = 'Name'
    RESPONSIBLE    = 'Responsible'

class TasklistColumnLabels(ConstantsGroup):
    __slots__ = ()
    TASKNUMBER     = 'Number'
    TASKNAME       = 'Name'
    TASKGROUPIDX   = 'Groupindex'

class TaskgroupColumnLabels(ConstantsGroup):
    __slots__ = ()
    GROUNAME       = 'Name'

__all__ = ("MRDCSVColumnLabels", "TasklistColumnLabels", "TaskgroupColumnLabels")

