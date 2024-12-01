# Copyright (c) 2023-2024 METTLER TOLEDO
#
# SPDX-License-Identifier: EUPL-1.2

import re
import pandas as pd
import numpy as np

import pathlib as pl

from projplan.filehandlers.base import filehandlers

from projplan              import TaskgroupColumnLabels, TasklistColumnLabels, ColumnLabelSpecifiers
from projplan.filehandlers import SearchRegex

class GitlabCsv(filehandlers):
    MILESTONE_UNDETERMINED = 'undetermined'
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

        rawcsv = pd.read_csv(filepath, engine='python',skip_blank_lines=True)

        taskgroups = pd.DataFrame(columns=list(TaskgroupColumnLabels.allConstantDict().values()) + [ColumnLabelSpecifiers.DEADLINEINDICATOR])
        tasklist   = pd.DataFrame(columns=list(TasklistColumnLabels.allConstantDict().values()) + [ColumnLabelSpecifiers.EFFORTINDICATOR, ColumnLabelSpecifiers.PRIORITYINDICATOR, ColumnLabelSpecifiers.CONSTRAINTINDICATOR])

        # Get all milestones (release versions) and sort them with increasing version number
        # If the undetermined milestone is not present, add it. This one will be used for all
        # tasks that are not assigned to a release.
        tmp = pd.DataFrame(rawcsv['Milestone'].unique()).dropna().to_numpy().transpose()
        tmp.sort()
        if GitlabCsv.MILESTONE_UNDETERMINED not in tmp:
            tmp[0,-1] = GitlabCsv.MILESTONE_UNDETERMINED
        taskgroups[TaskgroupColumnLabels.GROUNAME] = tmp.flatten()
        taskgroups = taskgroups.fillna('')
        # Ensure the undetermined milestone is the last one
        idxUndetermined  = taskgroups.index[taskgroups[TaskgroupColumnLabels.GROUNAME] == GitlabCsv.MILESTONE_UNDETERMINED]
        row_to_move = taskgroups.iloc[idxUndetermined]
        # Remove the row and append it to the end
        taskgroups = taskgroups.drop(taskgroups.index[idxUndetermined])
        taskgroups = taskgroups.reset_index(drop=True)
        taskgroups.loc[len(taskgroups.index)] = row_to_move.values[0]

        for _, row in rawcsv.iterrows():
            taskgroupindex = taskgroups.index[taskgroups['Name'] == row['Milestone']]
            if len(taskgroupindex) == 0:
                taskgroupindex = taskgroups.index[-1]
            else:
                taskgroupindex = taskgroupindex[-1]
            if 'priority::high' in row['Labels']:
                priority = 3
            elif 'priority::medium' in row['Labels']:
                priority = 2
            elif 'priority::low' in row['Labels']:
                priority = 1
            else:
                priority = 0
            tasklist.loc[len(tasklist.index)] = [
                        taskgroupindex,
                        row['Title'],
                        row['Issue ID'],
                        row['Time Estimate'] / 3600 / 8, # Time Estimate in seconds to 8h work days
                        priority,
                        ''
                        ]
        tasklist = tasklist.sort_values(by=[TasklistColumnLabels.TASKGROUPIDX, ColumnLabelSpecifiers.PRIORITYINDICATOR], ascending=[True, False])
        return (taskgroups, tasklist)
