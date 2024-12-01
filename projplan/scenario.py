# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import os
import numpy as np
import pandas as pd
import pathlib as pl
import math

from matplotlib.colors import ListedColormap

from projplan import TasklistColumnLabels, ColumnLabelSpecifiers

from projplan.filehandlers.raw import CsvRaw as DefaultFileBackend

from projplan.timehandling import Timeline
from projplan.resources import ResourcePool

class Roadmap(Timeline):
    def __init__(self, *args, **kwargs) -> None:
        """Initialize a scenario

        Parameters
        ----------
        name                : Name of the focus area as string, defaults to unknown-scenario.
        maxResources        : Resources available in FTEs either a constant or a list of tuples (startData, endDate, resource). None if no resources can be used for scheduling.
        focusareas          : List of focus areas in the scenario, list of resource pools.
        timelineStart       : Timeline start date as str or datetime.date, defaults to 1945-07-01.
        timelineEnd         : Timeline end date as str or datetime.date, defaults to today plus five years.
        planningFilePath    : Path to the planning file.
        planningFileBackend         : Backend to be used to read the planning file, defaults to projplan.planningFileBackend.csvRaw
        showUnusedResources : Whether unused resources are shown in the scenario or not, defaults to False
        """
        super(Roadmap, self).__init__(*args, **kwargs)
        self._initkwargs = kwargs

    @property
    def name(self) -> str:
        """Name of the scenario"""
        if not hasattr(self, '_name'):
            self._name = self._initkwargs.pop('name', 'unknown-scenario')
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def taskgroups(self) -> pd.DataFrame:
        if not hasattr(self, '_taskgroups'):
            self._taskgroups = pd.DataFrame({'Name':[], self.name: ''})
        return self._taskgroups

    @taskgroups.setter
    def taskgroups(self, value: pd.DataFrame) -> None:
        self._taskgroups = value

    @property
    def color(self) -> str:
        return self._initkwargs.get('color', '#000000')

    @color.setter
    def color(self, value: str) -> None:
        self._initkwargs['color'] = value

    @property
    def colordict(self) -> dict:
        return {self.name: self.color}

    @property
    def vertLines(self) -> dict:
        return self._initkwargs.get('vertLines', True)

    @vertLines.setter
    def vertLines(self, value: bool) -> None:
        self._initkwargs['vertLines'] = value

class Scenario(Roadmap):
    def __init__(self, *args, **kwargs) -> None:
        """Initialize a scenario

        Parameters
        ----------
        name                : Name of the focus area as string, defaults to unknown-scenario.
        maxResources        : Resources available in FTEs either a constant or a list of tuples (startData, endDate, resource). None if no resources can be used for scheduling.
        focusareas          : List of focus areas in the scenario, list of resource pools.
        timelineStart       : Timeline start date as str or datetime.date, defaults to 1945-07-01.
        timelineEnd         : Timeline end date as str or datetime.date, defaults to today plus five years.
        planningFilePath    : Path to the planning file path.
        planningFileBackend : Backend to be used to read the planning file, defaults to projplan.planningFileBackend.csvRaw
        showUnusedResources : Whether unused resources are shown in the scenario or not, defaults to False
        """
        super(Scenario, self).__init__(*args, **kwargs)
        self._initkwargs = kwargs
        if 'planningFilePath' not in self._initkwargs:
            raise Exception("Please define the parameter planningFilePath.")

    @property
    def planningFileBackend(self) -> object:
        return self._initkwargs.get('planningFileBackend', DefaultFileBackend)

    @property
    def resourcePools(self) -> list[ResourcePool]:
        if not hasattr(self, '_resourcePools'):
            self._resourcePools = self._initkwargs.pop('resourcePools', [])
        return self._resourcePools

    @property
    def resourcePoolsDict(self) -> dict[str, ResourcePool]:
        return {rp.name: rp for rp in self.resourcePools}

    @property
    def maxResources(self) -> int | float:
        if not hasattr(self, '_maxResources'):
            self._maxResources = self._initkwargs.pop('maxResources', np.inf)
        return self._maxResources

    @maxResources.setter
    def maxResources(self, value: int | float) -> None:
        self._maxResources = value

    @property
    def colormap(self) -> ListedColormap:
        return ListedColormap(colors=[rp.color for rp in self.resourcePools])

    @property
    def colordict(self) -> dict:
        return {rp.name: rp.color for rp in self.resourcePools}

    @property
    def resourcePoolsWithTasks(self) -> list[str]:
        if not hasattr(self, '_resourcePoolsToSchedule'):
            self._resourcePoolsToSchedule = self._initkwargs.pop('resourcePoolsWithTasks', []) # TODO PMi: something weird is going on, when using _resourcePoolsWithTasks this is just duplicated many times when scheduling...
        localResourcePoolsWithTasks = self._resourcePoolsToSchedule.copy()
        for columnName in self.tasklist.columns:
            if ColumnLabelSpecifiers.DEADLINEINDICATOR in columnName:
                rpwt = columnName.replace(ColumnLabelSpecifiers.DEADLINEINDICATOR, '').replace('-', '')
                if rpwt not in localResourcePoolsWithTasks:
                    localResourcePoolsWithTasks.append()
        return localResourcePoolsWithTasks

    @property
    def tasklist(self) -> pd.DataFrame:
        return self._tasklist

    @tasklist.setter
    def tasklist(self, value: pd.DataFrame) -> None:
        self._tasklist = value

    def scheduleTasks(self):
        self._initializeScheduling()
        self._scheduleForward()
        self._setTaskgroupDeadlines()

    def _synchroniseTimelines(self):
        """Make sure the timelines of the scenario and all the resource pools are synchronized."""
        # Synchronise all timelines
        for rp in self.resourcePools:
            rp.timelineStart = self.timelineStart
            rp.timelineEnd   = self.timelineEnd

    def _initializeScheduling(self) -> None:
        # Generate the base datastructures
        self._synchroniseTimelines()
        self.taskgroups, self.tasklist = self.planningFileBackend.readPlanningFile(self._initkwargs.get('planningFilePath'))
        self.roadmap  = pd.DataFrame({rp.name: rp.parameters.loc[:,ResourcePool.RESOURCES_COLUMN_LABEL].to_numpy() for rp in self.resourcePools}, index=self.timeline)

        # For the GitLab Backend we need to rename the generic constraint, priority and deadline column to the specific name for the resourcepool.
        renamingDict = {ColumnLabelSpecifiers.CONSTRAINTINDICATOR: self.resourcePoolsDict[self.resourcePoolsWithTasks[0]].nameConstraint,
                        ColumnLabelSpecifiers.DEADLINEINDICATOR: self.resourcePoolsDict[self.resourcePoolsWithTasks[0]].nameDeadline,
                        ColumnLabelSpecifiers.EFFORTINDICATOR: self.resourcePoolsDict[self.resourcePoolsWithTasks[0]].name,
                        ColumnLabelSpecifiers.PRIORITYINDICATOR: self.resourcePoolsDict[self.resourcePoolsWithTasks[0]].namePriority}
        # TODO PMi: renaming seems to be odd
        for key in renamingDict:
            if key in self.tasklist.columns:
                self.tasklist = self.tasklist.rename(columns={key: renamingDict[key]})
            if key in self.taskgroups.columns:
                self.taskgroups = self.taskgroups.rename(columns={key: renamingDict[key]})

        # Fill up roadmap to maxResources, if at some point too many resources are allocated keep them.
        allocatingResourcePools = [rp.name for rp in self.resourcePools if rp.allocateFreeResources]
        resourcesToDistribute = (self.maxResources - self.roadmap.sum(axis=1)) / len(allocatingResourcePools)
        resourcesToDistribute.loc[resourcesToDistribute < 0] = 0
        for allocatingResourcePool in allocatingResourcePools:
            self.roadmap.loc[:, allocatingResourcePool] = self.roadmap.loc[:, allocatingResourcePool] + resourcesToDistribute

        self.backlogs = {rpName: self.tasklist[[TasklistColumnLabels.TASKNUMBER, rpName, self.resourcePoolsDict[rpName].nameConstraint]][self.tasklist[rpName] != 0].copy(deep=True) for rpName in self.resourcePoolsWithTasks}

        # Setup helper datastructure with the resoucres to
        self.unusedResources   = pd.DataFrame({rpName: self.resourcePoolsDict[rpName].parameters.loc[:,ResourcePool.RESOURCES_COLUMN_LABEL].to_numpy() for rpName in self.backlogs}, index=self.timeline)
        self.parallelizability = pd.DataFrame({rpName: self.resourcePoolsDict[rpName].parameters.loc[:,ResourcePool.PARALLELIZABILITY_COLUMN_LABEL].to_numpy() for rpName in self.backlogs}, index=self.timeline)
        for idx, _ in self.unusedResources.iterrows():
            if idx.weekday() >= 5:
                self.unusedResources.loc[idx,:] = 0 # No resources available on weekends

    def _scheduleForward(self) -> None:
        dateIdx  = self.roadmap.index.sort_values(ascending=True)[0]

        # Schedule while we haven't reached the end of the roadmap and there are still tasks in the backlog
        while ((dateIdx in self.roadmap.index) and any([len(backlog) > 0 for backlog in self.backlogs.values()])):
            # Schedule all backlogs
            for rpName in self.backlogs:
                # Schedule as long as we have resources available and there are tasks in the backlog for this resource pool
                backlogIdx = 0
                while ((backlogIdx < len(self.backlogs[rpName])) and (self.unusedResources.loc[dateIdx, rpName] > 0) and (len(self.backlogs[rpName]) > 0)):
                    # How much work can we do for the current task
                    idx = self.backlogs[rpName].index[backlogIdx]
                    task = self.backlogs[rpName].loc[idx]
                    # TODO constraint stalling disabled as not needed for GitLab export. Need to be done properly, like this is just causes issues. There needs to be a clear format that is provided by the backend, preferably without numbering strings but with int numbering
                    #if (len(task[self.resourcePoolsDict[rpName].nameConstraint]) > 0 and
                    #    self.backlogs[rpName][TasklistColumnLabels.TASKNUMBER].str.contains(task[self.resourcePoolsDict[rpName].nameConstraint]).any()
                    #    self.backlogs[rpName][TasklistColumnLabels.TASKNUMBER].isin
                    #   ):
                    #   # Task is stalled due to constraint
                    #   backlogIdx = backlogIdx + 1
                    #   continue
                    resourcesAvailable = min([1, self.unusedResources.loc[dateIdx, rpName]/self.parallelizability.loc[dateIdx, rpName], task[rpName]])
                    # Do work, i.e. remove it from the backlog and from unused Resources
                    self.backlogs[rpName].loc[idx, rpName] = task[rpName] - (self.resourcePoolsDict[rpName].parameters.loc[dateIdx, ResourcePool.EFFICIENCY_COLUMN_LABEL] * resourcesAvailable)
                    self.unusedResources.loc[dateIdx, rpName] = self.unusedResources.loc[dateIdx, rpName] - resourcesAvailable

                    # Deal with rounding errors
                    ROUNDING_ERROR_MIN = 0.01
                    if self.backlogs[rpName].loc[idx, rpName] < ROUNDING_ERROR_MIN:
                        self.backlogs[rpName].loc[idx, rpName] = 0
                    if self.unusedResources.loc[dateIdx, rpName] < ROUNDING_ERROR_MIN:
                        self.unusedResources.loc[dateIdx, rpName] = 0

                    backlogIdx = backlogIdx + 1

                    # Remove finished tasks from backlog and set deadline in tasklist
                    finishedTasks = self.backlogs[rpName][self.backlogs[rpName][rpName] == 0]
                    self.tasklist.loc[self.tasklist[TasklistColumnLabels.TASKNUMBER].isin(finishedTasks[TasklistColumnLabels.TASKNUMBER]), self.resourcePoolsDict[rpName].nameDeadline] = dateIdx
                    self.backlogs[rpName] = self.backlogs[rpName][self.backlogs[rpName][rpName] != 0]
            # Increment dateIdx
            dateIdx = dateIdx + pd.DateOffset(days=1)

        print("Finished scheduling at date " + str(dateIdx))
        for rpName in self.backlogs:
            print("{} tasks remaining in backlog for {}".format(len(self.backlogs[rpName]), rpName))

    def _setTaskgroupDeadlines(self) -> None:
        for taskgroupIdx, _ in self.taskgroups.iterrows():
            for rpName in self.resourcePoolsWithTasks:
                tmp = self.tasklist[self.tasklist[TasklistColumnLabels.TASKGROUPIDX] == taskgroupIdx][self.resourcePoolsDict[rpName].nameDeadline]
                tmp = tmp[tmp.notna()]
                tmp = tmp[tmp != '']
                if type(tmp.max()) != float:
                    self.taskgroups.loc[taskgroupIdx, self.resourcePoolsDict[rpName].nameDeadline] = tmp.max()

