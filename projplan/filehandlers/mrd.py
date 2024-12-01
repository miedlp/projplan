# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import re
import pandas as pd

import pathlib as pl

from projplan.filehandlers import MRDCSVColumnLabels
from projplan.filehandlers import TasklistColumnLabels
from projplan.filehandlers import TaskgroupColumnLabels
from projplan.filehandlers import InputFileStandardLabels

def csvParse(*args, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parameters
    ----------
    mrdCsvFilepath: Path to the MRD csv file

    Return
    ------
    A tuple consisting of two dataframes: (Taskgroups, Tasklist)
    """
    mrdCsvFilepath = args[0]
    if mrdCsvFilepath is None:
        raise ValueError('MRD csv file path is not set')

    if type(mrdCsvFilepath) is str:
        mrdCsvFilepath = pl.Path(mrdCsvFilepath)

    if not mrdCsvFilepath.exists():
        raise ValueError('MRD path is not valid')

    mrdcsv = pd.read_csv(mrdCsvFilepath, sep='\s*,\s*', engine='python')
    for column in mrdcsv.columns:
        if InputFileStandardLabels.CONSTRAINTINDICATOR in column:
            mrdcsv[column] = mrdcsv[column].fillna('NONE')
        else:
            mrdcsv[column] = mrdcsv[column].fillna(0.0)

    tasklist   = pd.DataFrame(columns=list(TasklistColumnLabels.allConstantDict().values()) + list(mrdcsv.columns[3:]))
    taskgroups = pd.DataFrame(columns=TaskgroupColumnLabels.allConstantDict().values())

    for _, row in mrdcsv.iterrows():
        if re.match('^\d.\d$', row[MRDCSVColumnLabels.TASKNUMBER]) is not None:
            # This is a group line
            taskgroups.loc[len(taskgroups.index)] = [row[MRDCSVColumnLabels.TASKNAME]]
        elif re.match('^\d.\d.\d$', row[MRDCSVColumnLabels.TASKNUMBER]) is not None:
            # This is a task line
            tasklist.loc[len(tasklist.index)] = [taskgroups.index[-1], row[MRDCSVColumnLabels.TASKNAME], row[MRDCSVColumnLabels.TASKNUMBER]] + list(row.iloc[3:])
    # TODO PMi To change the order of the tasks, a priority column could be added and used for sorting here.
    return (taskgroups, tasklist)

