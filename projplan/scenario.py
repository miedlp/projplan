# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import os
import datetime as dt
import numpy as np
import pandas as pd
import pathlib as pl

from matplotlib.colors import ListedColormap
from pandas.api.types import is_numeric_dtype

from projplan.resources import ResourcePool
from projplan.filehandlers.mrd import csvParse as MRDDefaultBackend
from projplan.timehandling import Timeline

from projplan.filehandlers import TasklistColumnLabels

class Scenario(Timeline):
    def __init__(self, **kwargs) -> None:
        """Initialize a scenario

        Parameters
        ----------
        name              : Name of the focus area as string, defaults to unknown-scenario.
        maxResources      : Resources available in FTEs either a constant or a list of tuples (startData, endDate, resource). None if no resources can be used for scheduling.
        focusareas        : List of focus areas in the scenario, list of resource pools.
        timelineStart     : Timeline start date as str or datetime.date, defaults to 1945-07-01.
        timelineEnd       : Timeline end date as str or datetime.date, defaults to today plus five years.
        mrdpath           : Path to the MRD file.
        mrdBackend        : Backend to be used to read the MRD file, defaults to projplan.filehandler.mrd.csvParse
        showUnusedResources : Whether unused resources are shown in the scenario or not, defaults to False
        """
        self.timelineStart = kwargs.pop('timelineStart', '1945-07-01')
        self.timelineEnd   = kwargs.pop('timelineEnd', (pd.to_datetime('today').normalize()+pd.DateOffset(years=5)))
        for key in kwargs:
            setattr(self, '_' + key, kwargs[key])

    @property
    def showUnusedResources(self):
        return getattr(self, '_showUnusedResources', False)

    @property
    def unusedResources(self):
        if not hasattr(self, '_unusedResources'):
            self._unusedResources = ResourcePool(name=self.unusedResourcepoolName, basecost=0, schedulable=True,
                                             color='#000000', allocateFreeResources=False, resources=0)
        return self._unusedResources

    @property
    def unusedResourcepoolName(self):
        return 'unused'

    def synchroniseTimelines(self):
        """Make sure the timelines of the scenario and all the resource pools are synchronized."""
        # Synchronise all timelines
        for fa in self.focusareas:
            fa.timelineStart = self.timelineStart
            fa.timelineEnd   = self.timelineEnd

    @property
    def name(self) -> str:
        """Name of the focus area"""
        if not hasattr(self, '_name'):
            self._name = 'unknown-scenario'
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def holidays(self):
        return getattr(self, '_holidays', []) # TODO PMi: take into account the holidays

    @property
    def focusareas(self) -> list[ResourcePool]:
        if not hasattr(self, '_focusareas'):
            self._focusareas = []
        if self.showUnusedResources:
            return self._focusareas + [self.unusedResources]
        else:
            return self._focusareas

    @property
    def focusareasDict(self) -> dict[str, ResourcePool]:
        return {fa.name: fa for fa in self.focusareas}

    @property
    def colormap(self) -> ListedColormap:
        return ListedColormap(colors=[focusArea.color for focusArea in self.focusareas])

    @property
    def colordict(self) -> dict:
        return {fa.name: fa.color for fa in self.focusareas}

    @property
    def maxResources(self) -> pd.DataFrame:
        if not hasattr(self, '_maxResourcesTimeline'):
            self._maxResourcesTimeline = ResourcePool(name="Max. Resources", resources=getattr(self, '_maxResources', 10), timelineStart = self.timelineStart, timelineEnd = self.timelineEnd)
        return self._maxResourcesTimeline.resources

    @property
    def mrdBackend(self) -> object:
        return getattr(self, '_mrdBackend', MRDDefaultBackend)

    def updateMrd(self) -> None:
        self._mrdTaskgroups, self._mrdTasklist = self.mrdBackend(self.mrdpath)

    @property
    def mrdpath(self) -> pl.Path:
        if not hasattr(self, '_mrdpath'):
            self.mrdpath = pl.Path(os.getcwd()).joinpath('mrd.csv')
        return self._mrdpath

    @mrdpath.setter
    def mrdpath(self, value: str|pl.Path) -> None:
        if type(value) is str:
            self._mrdpath = pl.Path(value)
        elif type(value) is pl.Path:
            self._mrdpath = value

    @property
    def mrdTaskgroups(self) -> pd.DataFrame:
        if not hasattr(self, '_mrdTaskgroups'):
            self.updateMrd()
        return self._mrdTaskgroups

    @property
    def mrdTasklist(self) -> pd.DataFrame:
        if not hasattr(self, '_mrdTasklist'):
            self.updateMrd()
        return self._mrdTasklist

    @property
    def roadmap(self) -> pd.DataFrame:
        if not hasattr(self, '_roadmap'):
            self._resetRoadmapDatastructures()
        return self._roadmap

    @property
    def roadmapIdxToDateLut(self) -> pd.DataFrame:
        return self.roadmap.reset_index()['index']

    @property
    def mrdTaskgroupDeadlines(self) -> pd.DataFrame:
        if not hasattr(self, '_mrdTaskgroupDeadlines'):
            self._resetRoadmapDatastructures()
        return self._mrdTaskgroupDeadlines

    @property
    def mrdTaskDeadlines(self) -> pd.DataFrame:
        if not hasattr(self, '_mrdTaskDeadlines'):
            self._resetRoadmapDatastructures()
        return self._mrdTaskDeadlines

    @property
    def remainingRessources(self) -> pd.DataFrame:
        if not hasattr(self, '_remainingResources'):
            self._resetRoadmapDatastructures()
        return self._remainingResources

    def _resetRemainingRessources(self) -> None:
        resources = self.maxResources.copy().to_numpy()
        for fa in self.focusareas:
            resources = resources - fa.resources.to_numpy()
            resources = resources - fa.basecost.to_numpy()
        if (resources < 0).any():
            print("ERROR: Not enough resources for all focusareas, this will cause used resources to exceed the maximum that was set")
            resources[resources < 0] = 0
        self._remainingResources = pd.DataFrame(resources, columns=self.maxResources.columns, index=self.maxResources.index)

    @property
    def schedulableFocusareas(self) -> list[str]:
        return [faname for faname in self.mrdTasklist.columns[2:] if faname in self.focusareasDict.keys()]

    @property
    def allocatingFocusareas(self) -> list[str]:
        allocatingFocusareas = [fa.name for fa in self.focusareas if fa.allocateFreeResources and len(self._backlogs[fa.name]) > 0]
        if self.showUnusedResources:
            return allocatingFocusareas + [self.unusedResources]
        elif len(allocatingFocusareas) == 0:
            return [fa.name for fa in self.focusareas if fa.allocateFreeResources]
        else:
            return allocatingFocusareas

    def _resetRoadmapDatastructures(self, projectnames: list[str]) -> pd.DataFrame:
        self.synchroniseTimelines()
        self._roadmap               = pd.DataFrame({fa.name: fa.basecost.iloc[:,0].to_numpy() + fa.resources.iloc[:,0].to_numpy() for fa in self.focusareas}, index=self.timeline)
        self._roadmapRow            = self._roadmap.iloc[-1].copy()
        self._mrdTaskgroupDeadlines = pd.DataFrame(np.empty((self.mrdTaskgroups.shape[0], len(self.schedulableFocusareas)), dtype=pd.DatetimeIndex), columns=self.schedulableFocusareas, index=self.mrdTaskgroups.index)
        self._mrdTaskDeadlines      = pd.DataFrame(np.empty((self.mrdTasklist.shape[0],   len(self.schedulableFocusareas)), dtype=pd.DatetimeIndex), columns=self.schedulableFocusareas, index=self.mrdTasklist.index)
        self._backlogs              = {projectname: self.mrdTasklist[[TasklistColumnLabels.TASKNUMBER, projectname, self.focusareasDict[projectname].constraintColumnName]][self.mrdTasklist[projectname] != 0].copy(deep=True) for projectname in projectnames}
        self._schedulableResources  = {projectname: self.focusareasDict[projectname].resources.copy(deep=True) for projectname in projectnames}

        for dateIdx in self.roadmap.index.sort_values(ascending=True):
            if (dateIdx.weekday() >= 5)  or (dateIdx in self.holidays):
                # This day is a weekend or a holiday, do not schedule work
                for projectname in projectnames:
                    self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] = 0
        self._resetRemainingRessources()

    def _distributeRemainingResources(self, fromDate: pd.DatetimeIndex) -> None:
        if len(self.allocatingFocusareas) == 0:
            print("No focusareas to distribute the remaining resources on")
            return
        if self.showUnusedResources:
            self.roadmap.loc[fromDate:, self.unusedResourcepoolName] = self.remainingRessources.loc[fromDate:,self.remainingRessources.columns[0]].to_numpy()
        else:
            resourcesToAllocatePerFA = self.remainingRessources.loc[fromDate:,self.remainingRessources.columns[0]].to_numpy() / len(self.allocatingFocusareas)
            for name in self.allocatingFocusareas:
                self.roadmap.loc[fromDate:, name] = self.focusareasDict[name].resources.loc[fromDate:,self.focusareasDict[name].resources.columns[0]].to_numpy() + resourcesToAllocatePerFA

    def scheduleTasks(self, projectnames: list[str] = []):
        if len(projectnames) == 0:
            projectnames = self.schedulableFocusareas
        self._resetRoadmapDatastructures(projectnames)
        self._scheduleForward(projectnames)
        self._setTaskgroupDeadlines(projectnames)

    def _scheduleForward(self, projectnames: list[str]) -> None:
        dateIdx       = self.roadmap.index.sort_values(ascending=True)[0]

        finished = False
        while not finished:
            # Get schedulable tasks
            # Distribute resouces
            # Schedule tasks



            # First pass, schedule regular resources
            for projectname in projectnames:
                self._scheduleSingleDate(dateIdx, projectname)
            # Distribute resources to projects that still require resources
            if len(self.allocatingFocusareas) > 0:
                resourcesToDistribute = self.remainingRessources.loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] / len(self.allocatingFocusareas)
                for name in self.allocatingFocusareas:
                    self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] = self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] + resourcesToDistribute
                    self.roadmap.loc[dateIdx, name] = self.roadmap.loc[dateIdx, name] + resourcesToDistribute
            # Second pass, schedule additional available resources
            for projectname in projectnames:
                self._scheduleSingleDate(dateIdx, projectname)
            # Move unused resources
            if self.showUnusedResources:
                for name in self.allocatingFocusareas:
                    self.roadmap.loc[dateIdx, self.unusedResourcepoolName] = self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL]
                    self.roadmap.loc[dateIdx, name] = self.roadmap.loc[dateIdx, name] - self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL]
            # Increment dateIdx
            dateIdx = dateIdx + pd.DateOffset(days=1)
            # Check if finished (timeline end reached or backlogs empty)
            finished = (dateIdx not in self.roadmap.index) or all([len(backlog) == 0 for backlog in self._backlogs.values()])
        print("Finished scheduling at date " + str(dateIdx))
        self._distributeRemainingResources(dateIdx)

    def _scheduleSingleDate(self, dateIdx, projectname):
        backlogIdx = 0  # We only want one person to work at one task at a time
        while ((self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] > 0)
               and (len(self._schedulableResources[projectname].index) > 0)
               and (len(self._backlogs[projectname]) > 0)
               ):
            # Get Index of work-item in backlog
            mrdIdx   = self._backlogs[projectname].index[backlogIdx]

            if any([backlog[TasklistColumnLabels.TASKNUMBER].str.contains(self._backlogs[projectname].loc[mrdIdx, self.focusareasDict[projectname].constraintColumnName]).any() for backlog in self._backlogs.values()]):
                # The task highest on the list cannot be scheduled at the moment.
                break

            # How much work can we do for the current task
            onePersonWork = self.focusareasDict[projectname].efficiency .loc[dateIdx, ResourcePool.EFFICIENCY_COLUMN_LABEL]*1
            maxActualWork = self.focusareasDict[projectname].efficiency .loc[dateIdx, ResourcePool.EFFICIENCY_COLUMN_LABEL]*self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL]
            workToDo = min([self._backlogs[projectname].loc[mrdIdx, projectname], onePersonWork, maxActualWork])
            # Remove work from the task backlog and add it to the roadmap
            self._backlogs[projectname].loc[mrdIdx, projectname] = self._backlogs[projectname].loc[mrdIdx, projectname] - workToDo
            # Remove work from resource pool
            self._schedulableResources[projectname].loc[dateIdx, ResourcePool.RESOURCES_COLUMN_LABEL] = self._schedulableResources[projectname].loc[dateIdx][ResourcePool.RESOURCES_COLUMN_LABEL] - workToDo
            if self._backlogs[projectname].loc[mrdIdx, projectname] == 0:
                # Task finished, set deadline and remove from backlog
                self.mrdTaskDeadlines.loc[mrdIdx, projectname] = dateIdx
                self._backlogs[projectname] = self._backlogs[projectname].drop(index=mrdIdx)
                backlogIdx = 0
            else:
                backlogIdx = (backlogIdx + 1) if ((backlogIdx + 1) < len(self._backlogs[projectname])) else 0

    def _setTaskgroupDeadlines(self, projectnames: list[str]) -> None:
        for projectname in projectnames:
            for taskgroupIdx, _ in self.mrdTaskgroups.iterrows():
                tmp = self.mrdTaskDeadlines[self.mrdTasklist[TasklistColumnLabels.TASKGROUPIDX] == taskgroupIdx][projectname]
                tmp = tmp[tmp.notna()]  # Tasks which are not executed in this project (0 tasks), do not have a deadline and are therefore NaN
                self.mrdTaskgroupDeadlines.loc[taskgroupIdx, projectname] = tmp.max()

