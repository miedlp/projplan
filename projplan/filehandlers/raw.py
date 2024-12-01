# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import re
import pandas as pd
import numpy as np

import pathlib as pl

from projplan.filehandlers.base import filehandlers

from projplan             import TaskgroupColumnLabels, TasklistColumnLabels, ColumnLabelSpecifiers
from projplan.filehandlers import SearchRegex

class CsvRaw(filehandlers):
    NUM_FIXED_COLUMNS = 2
    @staticmethod
    def getDataFileEnding() -> str:
        return '.csv'

    @staticmethod
    def readPlanningFile(filepath: pl.Path) -> pd.DataFrame:
        """
        Parameters
        ----------
        filepath: Path to the planning csv file

        Return
        ------
        A tuple consisting of two dataframes: (Taskgroups, Tasklist)
        """
        if type(filepath) is str:
            filepath = pl.Path(filepath)

        if not filepath.exists():
            raise ValueError('planning path is not valid')

        rawcsv = pd.read_csv(filepath, sep='\s*,\s*', engine='python')

        # Ensure that there are all columns present
        for column in rawcsv.columns[CsvRaw.NUM_FIXED_COLUMNS:]:
            if ColumnLabelSpecifiers.CONSTRAINTINDICATOR in column:
                # Constraint column
                complementaryColumns = [column.replace(ColumnLabelSpecifiers.CONSTRAINTINDICATOR, '').replace('-',''),
                                        column.replace(ColumnLabelSpecifiers.CONSTRAINTINDICATOR, ColumnLabelSpecifiers.DEADLINEINDICATOR)
                                       ]
            elif ColumnLabelSpecifiers.DEADLINEINDICATOR in column:
                # Deadline column
                complementaryColumns = [column.replace(ColumnLabelSpecifiers.DEADLINEINDICATOR, '').replace('-',''),
                                        column.replace(ColumnLabelSpecifiers.DEADLINEINDICATOR, ColumnLabelSpecifiers.CONSTRAINTINDICATOR)
                                       ]
            else:
                # Effort column
                complementaryColumns = [column + '-' + ColumnLabelSpecifiers.CONSTRAINTINDICATOR,
                                        column + '-' + ColumnLabelSpecifiers.DEADLINEINDICATOR
                                       ]
            for complementaryColumn in complementaryColumns:
                if complementaryColumn not in rawcsv.columns:
                    rawcsv.insert(len(rawcsv.columns), complementaryColumn, np.full(rawcsv.index.shape, ''))

        for column in rawcsv.columns:
            if ColumnLabelSpecifiers.CONSTRAINTINDICATOR in column or ColumnLabelSpecifiers.DEADLINEINDICATOR in column:
                rawcsv[column] = rawcsv[column].fillna('')
            else:
                rawcsv[column] = rawcsv[column].fillna(0.0)

        tasklist   = pd.DataFrame(columns=list(TasklistColumnLabels.allConstantDict().values()) + list(rawcsv.columns[CsvRaw.NUM_FIXED_COLUMNS:]))
        taskgroups = pd.DataFrame(columns=TaskgroupColumnLabels.allConstantDict().values())

        for _, row in rawcsv.iterrows():
            if re.match(SearchRegex.REGEX_TASKGROUPNUMBER, row[CSVColumnLabels.TASKNUMBER]) is not None:
                # This is a group line
                taskgroups.loc[len(taskgroups.index)] = [row[CSVColumnLabels.TASKNAME]]
            elif re.match(SearchRegex.REGEX_TASKNUMBER, row[CSVColumnLabels.TASKNUMBER]) is not None:
                # This is a task line
                tasklist.loc[len(tasklist.index)] = [taskgroups.index[-1], row[CSVColumnLabels.TASKNAME], row[CSVColumnLabels.TASKNUMBER]] + list(row.iloc[CsvRaw.NUM_FIXED_COLUMNS:])

        for column in tasklist.columns:
            if ColumnLabelSpecifiers.DEADLINEINDICATOR in column:
                taskgroups.insert(len(taskgroups.columns), column, np.full(taskgroups.index.shape, ''))
        return (taskgroups, tasklist)
