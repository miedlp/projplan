# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

from projplan import ConstantsGroup

class SearchRegex(ConstantsGroup):
    REGEX_TASKNUMBER      = r'^\d+.\d+.\d+$'
    REGEX_TASKGROUPNUMBER = r'^\d+.\d+$'

__all__ = ("SearchRegex")

