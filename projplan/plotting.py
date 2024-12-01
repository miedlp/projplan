# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import datetime as dt
import numpy as np
import pandas as pd
import re
import math
import pathlib as pl
import os

from matplotlib import pyplot as plt

from projplan.scenario import Scenario, Roadmap
from projplan import TaskgroupColumnLabels

class RoadmapPlot(object):
    EXPORT_FILE_EXTENSION = 'png'

    def __init__(self, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        path : Path in which the plots will be saved, defaults to current directory.
        name : Plot name as str, if not set will generate a name from the scenarios.
        scenarios : List of scenarios which should be included in the plot.
        """
        if "scenario" not in kwargs:
            raise Exception("Please define the scenarios to print as a list")
        self.scenario = kwargs.pop('scenario')
        self._dateLookup = pd.DataFrame(self.scenario.roadmap.index)
        self._kwargs = kwargs


    @property
    def path(self) -> pl.Path:
        if not hasattr(self, '_path'):
            self._path = self._kwargs.pop('path', pl.Path(os.getcwd()))
        self._path.mkdir(parents=True, exist_ok=True)
        return self._path

    @property
    def name(self) -> str:
        return self._kwargs.get('name', self.scenario.name.replace(' ', '-').lower())

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        
    @property
    def filename(self) -> str:
        return self.name  + '.' + RoadmapPlot.EXPORT_FILE_EXTENSION

    @property
    def filepath(self) -> pl.Path:
        return self.path.joinpath(self.filename)

    @property
    def tickFreq(self) -> str:
        return self._kwargs.get('tickFreq', 'QE')

    @tickFreq.setter
    def tickFreq(self, value: str) -> None:
        self._kwargs['tickFreq'] = value

    @property
    def plotwidth(self) -> str:
        return self._kwargs.get('plotwidth', 25)

    @plotwidth.setter
    def plotwidth(self, value: int) -> None:
        self._kwargs['plotwidth'] = value

    @property
    def plotheight(self) -> str:
        return self._kwargs.get('plotheight', 6)

    @plotheight.setter
    def plotheight(self, value: int) -> None:
        self._kwargs['plotheight'] = value

    @property
    def dpi(self) -> int:
        return self._kwargs.get('dpi', 100)

    @dpi.setter
    def dpi(self, value: int) -> None:
        self._kwargs['dpi'] = value

    @property
    def startDate(self) -> str:
        return self._kwargs.get('startDate', self.scenario.timelineStart)

    @startDate.setter
    def startDate(self, value: dt.datetime) -> None:
        self._kwargs['startDate'] = value

    @property
    def endDate(self) -> str:
        return self._kwargs.get('endDate', self.scenario.timelineEnd)

    @endDate.setter
    def endDate(self, value: dt.datetime) -> None:
        self._kwargs['endDate'] = value

    @property
    def stackedMilestones(self) -> int:
        return self._kwargs.get('stackedMilestones', 4)

    @stackedMilestones.setter
    def stackedMilestones(self, value: int) -> None:
        self._kwargs['stackedMilestones'] = value

    @property
    def milestoneVertSpacing(self) -> int:
        return self._kwargs.get('milestoneVertSpacing', 1)

    @milestoneVertSpacing.setter
    def milestoneVertSpacing(self, value: int) -> None:
        self._kwargs['milestoneVertSpacing'] = value

    @property
    def ylabelOffset(self) -> int:
        return self._kwargs.get('ylabelOffset', 30)

    @property
    def yMilestoneOffset(self) -> int:
        return self._kwargs.get('ylabelOffset', 10)

    @ylabelOffset.setter
    def ylabelOffset(self, value: int) -> None:
        self._kwargs['ylabelOffset'] = value

    @property
    def ytickinterval(self) -> int:
        return self._kwargs.get('ytickinterval', 2)

    @ytickinterval.setter
    def ytickinterval(self, value: int) -> None:
        self._kwargs['ytickinterval'] = value

    @property
    def showReleasing(self) -> str:
        return self._kwargs.get('showReleasing', [])

    @showReleasing.setter
    def showReleasing(self, value: list[tuple[int, dt.datetime, bool]]) -> None:
        self._kwargs['showReleasing'] = value

    @property
    def rollingReleases(self) -> pd.DateOffset:
        return self._kwargs.get('rollingReleases', None)

    @rollingReleases.setter
    def rollingReleases(self, value: dt.datetime) -> None:
        self._kwargs['rollingReleases'] = value

    @property
    def extraMilestoneSlots(self) -> int:
        return self._kwargs.get('extraMilestoneSlots', 0)

    @extraMilestoneSlots.setter
    def extraMilestoneSlots(self, value: int) -> None:
        self._kwargs['extraMilestoneSlots'] = value

    @property
    def numMilestoneRPs(self) -> int:
        return len(self.scenario.resourcePoolsWithTasks) + self.extraMilestoneSlots + len(self.projectRoadmaps) + len(self.scenarioRoadmaps)

    @property
    def milestoneVertSpace(self) -> int | float:
        return self.stackedMilestones * self.milestoneVertSpacing

    @property
    def yMax(self) -> int | float:
        return self.scenario.roadmap.sum(axis=1).max()

    @property
    def yMin(self) -> int | float:
        return -(self.numMilestoneRPs * self.milestoneVertSpace)

    @property
    def projectRoadmaps(self) -> list[Roadmap]:
        return self._kwargs.get('projectRoadmaps', [])

    @property
    def scenarioRoadmaps(self) -> list[Scenario]:
        return self._kwargs.get('scenarioRoadmaps', [])

    def dateToIdx(self, date: dt.datetime) -> int:
        return self._dateLookup[self._dateLookup[0] == date].index[0]

    def _generateTicks(self, startDate, endDate):
        if type(startDate) != str:
            startDate = startDate.strftime('%Y-%m-%d')
        if type(endDate) != str:
            endDate = endDate.strftime('%Y-%m-%d')
        _genTicks = pd.date_range(start=startDate, end=endDate, freq=self.tickFreq)
        _genLabels  = [self.scenario.roadmap.index[self.scenario.roadmap.index == tick].to_period(self.tickFreq.replace('E', '')) for tick in _genTicks]
        return {
            'idx': [0]  + [self.dateToIdx(tick) for tick in _genTicks],
            'lbl': [''] + [str(lbl.strftime('Q%q-%y')[0]) for lbl in _genLabels]
        }

    def plot(self, save: bool = False, dir: str | pl.Path = '') -> None:
        roadMapToPlot = self.scenario.roadmap.set_axis([rp.label for rp in self.scenario.resourcePools], axis=1).reset_index(drop=True)

        #self.figure = plt.figure(figsize=(plotwidth, plotheight), dpi=dpi);
        self.figure, self.axes = plt.subplots(1, 1, sharex=True, figsize=(self.plotwidth, self.plotheight), dpi=self.dpi)
        roadMapToPlot.plot.area(cmap=self.scenario.colormap, ax=self.axes);
        self.axes.legend(bbox_to_anchor=(1,1), loc="upper left", fontsize=15);
        self.axes.set_xlim([self.dateToIdx(self.startDate), self.dateToIdx(self.endDate)]);

        # Ticks
        ticks = self._generateTicks(self.startDate, self.endDate)
        self.axes.set_xticks(minor=False, ticks=ticks['idx'], labels=ticks['lbl'], fontsize=15);

        # Draw horizontal separating lines
        for idx in range(self.numMilestoneRPs):
            milestoneRange = [0 - (idx * self.milestoneVertSpace)]
            self.axes.hlines(xmin=self.dateToIdx(self.startDate), xmax=self.dateToIdx(self.endDate),
                        y=milestoneRange, colors='black', linewidths=0.25, linestyles='dashed')

        # Draw milestones for the scenario
        allScenarios = [self.scenario] + self.scenarioRoadmaps
        idx = 0
        for scenario in allScenarios:
            for milestoneRpName in scenario.resourcePoolsWithTasks:
                rp = scenario.resourcePoolsDict[milestoneRpName]
                self._plotMilestonesForRoadmap(scenario, idx, rp.nameDeadline, milestoneRpName, scenario.colordict[milestoneRpName], len(self.showReleasing) > 0)
                idx = idx + 1

        # Draw milestones for the project roadmaps
        for idx, projectRoadmap in enumerate(self.projectRoadmaps):
            self._plotMilestonesForRoadmap(projectRoadmap, idx+len(self.scenario.resourcePoolsWithTasks), projectRoadmap.name, projectRoadmap.name, projectRoadmap.color, False)

        self.axes.hlines(xmin=self.dateToIdx(self.startDate), xmax=self.dateToIdx(self.endDate), y=0, colors='black', linewidths=0.75)
        self.axes.set_ylim([self.yMin, self.yMax]);
        self.axes.set_ylabel('')
        yticks = list(range(0,math.ceil(self.yMax)+1,self.ytickinterval))
        self.axes.set_yticks(minor=False, ticks=yticks, labels=yticks, fontsize=15)
        self.axes.text(self.dateToIdx(self.startDate)-self.ylabelOffset, self.yMax/2, 'FTE', rotation=0, fontsize=25, verticalalignment='center', horizontalalignment='right')
        if save:
            exportpath = pl.Path(os.getcwd()).joinpath(dir)
            exportpath.mkdir(parents=True, exist_ok=True)
            self.figure.savefig(self.filepath)

    def _plotMilestonesForRoadmap(self, projectRoadmap: pd.DataFrame, milestoneRangeIdx, deadlineColName: str, milestoneRpName: str, color: str, showReleasing: bool):
        milestoneRange = [0 - (milestoneRangeIdx * self.milestoneVertSpace)]
        milestoneRange.append(milestoneRange[0] - self.milestoneVertSpace)

        milestoneGrid = [milestoneRange[0] - self.milestoneVertSpacing * 0.5 - self.milestoneVertSpacing*idx for idx in range(self.stackedMilestones)]
        milestones = self._getMilestoneParameters(projectRoadmap.taskgroups, deadlineColName, milestoneGrid, showReleasing)
        # Draw Milestones labels on timeline
        for idx, milestone in milestones.iterrows():
            if milestone['x'] == '':
                continue
            self.axes.scatter(x=milestone['x'], y=milestone['y'], marker="D", color=color);
            self.axes.annotate(milestone['label'],
                        xy=(milestone['x'],milestone['y']),
                        xytext=(10, np.sign(milestone['y'])*3),
                        textcoords="offset points", horizontalalignment="left",
                        verticalalignment="center",
                        fontsize=15)
            if milestone['vertline'] and projectRoadmap.vertLines:
                # Draw vertical lines for milestones
                self.axes.vlines(milestone['x'], self.yMin, self.yMax, color='white', linestyles='solid')  # White background line
                self.axes.vlines(milestone['x'], self.yMin, self.yMax, color=color, linestyles='dashed')  # Colour inidicator line.
        self.axes.text(self.dateToIdx(self.startDate)-self.yMilestoneOffset, (milestoneRange[1] - milestoneRange[0])/2+milestoneRange[0], milestoneRpName, rotation=0, fontsize=15, verticalalignment='center', horizontalalignment='right')

    def _getMilestoneParameters(self, taskGroups: pd.DataFrame, deadlineColName: str, milestoneGrid: list[int|float], showReleasing: bool) -> pd.DataFrame:
        milestones = {'x':[], 'y':[], 'label':[], 'vertline':[], 'position':[]}
        milestoneDefs = taskGroups.copy(deep=True)
        if self.rollingReleases is not None:
            milestoneDate = milestoneDefs.iloc[-2][deadlineColName] + self.rollingReleases
            currentRelease = [int(num) for num in re.findall('\d+', milestoneDefs.iloc[-2][TaskgroupColumnLabels.GROUNAME])]
            currentRelease[0] = currentRelease[0] + 1
            # TODO PMi fugly....
            while milestoneDate < self.endDate:
                milestoneDefs.loc[len(milestoneDefs)] = {TaskgroupColumnLabels.GROUNAME: "v{}.{}.{}".format(str(currentRelease[0]), str(currentRelease[1]), str(currentRelease[2])), deadlineColName: milestoneDate}
                milestoneDate = milestoneDate + self.rollingReleases
                currentRelease[0] = currentRelease[0] + 1

        # TODO PMi: there is a need for a version class to control version upgrades with rules
        for _, row in milestoneDefs.iterrows():
            if row[deadlineColName] == '':
                continue
            if showReleasing and re.match('v[1-9]\d*.\d+.0', row['Name']):
                releaseDate = row[deadlineColName]
                versionNumbers = [int(num) for num in re.findall('\d+', row[TaskgroupColumnLabels.GROUNAME])]
                for labelLevel, (versionOffsetBase, patchlevelOffset, delay, vertLine) in enumerate(self.showReleasing):
                    releaseDate = releaseDate + delay

                    if ((versionOffsetBase != 0) or (patchlevelOffset != 0)):
                        if versionNumbers[1] == 0:
                            # Increasing major version
                            major      = versionNumbers[0] - 1
                            minor      = versionOffsetBase
                            patchlevel = 0
                        else:
                            # Increasing minor version
                            major      = versionNumbers[0]
                            minor      = versionNumbers[1] - 1
                            patchlevel = versionOffsetBase
                    else:
                        major = versionNumbers[0]
                        minor = versionNumbers[1]
                        patchlevel = versionOffsetBase
                    newVersionString = "v{}.{}.{}".format(str(major), str(minor), str(patchlevel + patchlevelOffset))
                    milestones['label'].append(newVersionString)
                    milestones['vertline'].append(vertLine)
                    milestones['position'].append(labelLevel)
                    milestones['x'].append(self.dateToIdx(releaseDate))
                    milestones['y'].append(milestoneGrid[milestones['position'][-1]])
            elif re.match('undetermined', row['Name']):
                # Do not plot the undetermined milestone (this is the backlog and most likely nobody cares how much is in the backlog)
                pass
            else:
                if len(milestones['position']) == 0:
                    lastLabelLevel = -1
                else:
                    lastLabelLevel = milestones['position'][-1]
                milestones['label'].append(row[TaskgroupColumnLabels.GROUNAME])
                milestones['vertline'].append(True)
                milestones['position'].append((lastLabelLevel + 1) % len(milestoneGrid))
                milestones['x'].append(self.dateToIdx(row[deadlineColName]))
                milestones['y'].append(milestoneGrid[milestones['position'][-1]])
        return pd.DataFrame(milestones)
