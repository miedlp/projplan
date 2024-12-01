# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import math

import datetime as dt
import numpy as np
import pandas as pd
import pathlib as pl
import os

import matplotlib
from matplotlib import pyplot as plt
from matplotlib import cm

from projplan.scenario import Scenario
from projplan.filehandlers import TaskgroupColumnLabels

class Roadmap(object):
    EXPORT_FILE_EXTENSION = 'png'

    def __init__(self, **kwargs) -> None:
        """
        Parameters
        ----------
        path : Path in which the plots will be saved, defaults to current directory.
        name : Plot name as str, if not set will generate a name from the scenarios.
        scenarios : List of scenarios which should be included in the plot.
        """
        self.scenarios = kwargs.pop('scenarios', [])
        for key in kwargs:
            setattr(self, '_' + key, kwargs[key])

    @property
    def path(self) -> pl.Path:
        if not hasattr(self, '_path'):
            self._path = pl.Path(os.getcwd())
        self._path.mkdir(parents=True, exist_ok=True)
        return self._path

    @property
    def scenarios(self):
        if not hasattr(self, '_scenarios'):
            self._scenarios = []
        return self._scenarios

    @scenarios.setter
    def scenarios(self, value: list[Scenario]) -> None:
        self._scenarios = {scenario.name: scenario for scenario in value}

    @property
    def plotParams(self):
        if not hasattr(self, '_plotParams'):
            self._plotParams = [{} for _ in self.scenarios]
        return self._plotParams

    @property
    def name(self) -> str:
        if not hasattr(self, '_name'):
            self._name = ''
            for scenario in self.scenarios:
                self._name = self._name + scenario.replace(' ', '-').lower() + '_'
            self._name = self._name[:-1]
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def filename(self) -> str:
        return self.name  + '.' + Roadmap.EXPORT_FILE_EXTENSION

    @property
    def filepath(self) -> pl.Path:
        return self.path.joinpath(self.filename)

    @property
    def figure(self):
        return getattr(self, '_figure', None)

    @figure.setter
    def figure(self, value) -> None:
        self._figure = value

    def save(self):
        if self.figure is not None:
            self.figure.savefig(self.filepath)
        else:
            print("No figure generated yet, cannot save")

    @property
    def axes(self):
        return getattr(self, '_axes', [])

    @axes.setter
    def axes(self, value) -> None:
        if type(value) is matplotlib.axes._axes.Axes:
            self._axes = np.array([value])
        elif type(value) is np.ndarray or type(value) is list:
            self._axes = value
        else:
            raise Exception("Trying to set non-axis object to axis...")

    def plot(self, **kwargs):
        """
        Parameter
        ---------
        plotSelection : dict of lists with {<scenario to plot>: [<focusarea with milestone to be plotted>]}.
        """
        plotwidth          = kwargs.pop('plotwidth', 18)
        plotheight         = kwargs.pop('plotheight', 4)
        ylabelpos          = kwargs.pop('ylabelpos', -100)
        timelineStart      = kwargs.pop('timelineStart', min([scenario.timelineStart for scenario in self.scenarios.values()]))
        timelineEnd        = kwargs.pop('timelineEnd', max([scenario.mrdTaskgroupDeadlines.iloc[-1,:].max() for scenario in self.scenarios.values()]))
        plotSelection      = kwargs.pop('plotSelection', {})
        oneLegendOnly      = kwargs.pop('oneLegendOnly', False)
        numResourcePlots   = len(plotSelection.keys())

        self.figure, self.axes = plt.subplots(numResourcePlots, 1, sharex=True, figsize=(plotwidth,plotheight*numResourcePlots), dpi=100)

        for pltIdx, scenarioName in enumerate(plotSelection):
            scenario = self.scenarios[scenarioName]
            _dateLookup = pd.DataFrame(scenario.roadmap.index)
            scenarioTimelineStartIdx = _dateLookup[_dateLookup[0] == timelineStart].index[0]  # TODO PMi duplicated code from _generateTicks

            self._plotResourceDistribution(pltIdx, scenario, **kwargs)
            self._plotMilestones(pltIdx, plotSelection[scenarioName], **kwargs)

            self.axes[pltIdx].set_ylabel('')
            self.axes[pltIdx].text(ylabelpos, scenario.maxResources.max(axis=0).max()/2, 'FTE', rotation=0, fontsize=25, verticalalignment='center')
            self.axes[pltIdx].set_xlim([scenarioTimelineStartIdx, (timelineEnd - timelineStart).days]);
            self.axes[pltIdx].set_ylim(self.plotParams[pltIdx]['ylim'])
            if oneLegendOnly and pltIdx > 0:
                self.axes[pltIdx].get_legend().remove()

        self.figure.tight_layout()
        # Not needed, just causes a warning: self.figure.show()

    def _generateTicks(self, scenario, tickFreq):
        _genTicks = pd.date_range(start=scenario.roadmap.index[0].strftime('%Y-%m-%d'), end=scenario.roadmap.index[-1].strftime('%Y-%m-%d'), freq=tickFreq)
        _genLabels  = [scenario.roadmap.index[scenario.roadmap.index == tick].to_period(tickFreq.replace('E', '')) for tick in _genTicks]
        _dateLookup = pd.DataFrame(scenario.roadmap.index)
        return {
            'idx': [0]  + [_dateLookup[_dateLookup[0] == tick].index[0] for tick in _genTicks],
            'lbl': [''] + [str(lbl.strftime('Q%q-%y')[0]) for lbl in _genLabels]
        }

    def _plotResourceDistribution(self, *args, **kwargs):
        pltIdx         = args[0]
        scenario       = args[1]
        axis           = self.axes[pltIdx]
        tickMajorFreq  = kwargs.pop("tickMajorFreq", 'Q')
        legendOutside  = kwargs.pop("legendOutside", False)
        boxaxespad     = kwargs.pop("boxaxespad", 1.5)
        bbox_to_anchor = kwargs.pop("bbox_to_anchor", (0.0,1.0))

        # Area plot to show transition from Rainbow to BeyondRainbow
        scenario.roadmap.reset_index(drop=True).plot.area(cmap=scenario.colormap, ax=axis);

        if legendOutside:
            axis.legend(framealpha=1, fontsize=14, bbox_to_anchor=bbox_to_anchor, borderaxespad=boxaxespad)
        else:
            axis.legend(loc='upper right', framealpha=1, fontsize=14);

        axis.hlines(0, 0, len(scenario.roadmap.index), colors='black', linewidths=0.5)

        # Ticks
        ticks = self._generateTicks(scenario, tickMajorFreq)
        axis.set_xticks(minor=False, ticks=ticks['idx'], labels=ticks['lbl'], fontsize=15);

        yticks = list(range(0,math.ceil(scenario.maxResources.max(axis=0).max())+1,2))
        axis.set_yticks(minor=False, ticks=yticks, labels=yticks, fontsize=15)
        self.plotParams[pltIdx]['ylim'] = [0, scenario.maxResources.max(axis=0).max()]

    def _plotMilestones(self,*args, **kwargs):
        pltIdx = args[0]
        projectList = args[1]

        axis = self.axes[pltIdx]

        stackedLabels = kwargs.pop("stackedLabels", 3)
        labelSpacing = kwargs.pop("labelSpacing", 1)

        offset = 0
        self.plotParams[pltIdx]['milestones'] = {}
        for scenarioName, project in projectList:
            scenario = self.scenarios[scenarioName]

            lineMin = offset
            lblMin = lineMin-labelSpacing*0.5
            lblMax = lblMin-(labelSpacing*(stackedLabels-1))
            lineMax = lblMax-(labelSpacing*0.5)
            lblCenter = lblMin-(abs(abs(lblMax)-abs(lblMin))/2)
            offset = lineMax
            self.plotParams[pltIdx]['milestones'][project] = {'line':[lineMin, lineMax],
                                                                    'label':[lblMin, lblCenter, lblMax],
                                                                    'grid':[lblMin-labelSpacing*idx for idx in range(stackedLabels)]
                                                                    }

        # Increase size of canvas
        self.plotParams[pltIdx]['ylim'] = [-(stackedLabels*labelSpacing*len(projectList)), scenario.maxResources.max(axis=0).max()]

        for scenarioName, project in projectList:
            scenario = self.scenarios[scenarioName]
            # Draw border lines for milestone intervals
            for idx in range(2):
                axis.hlines(self.plotParams[pltIdx]['milestones'][project]['line'][idx],
                            0, len(scenario.roadmap.index), colors='black', linewidths=0.25, linestyles='dashed')

                # Get milestone x-values
                milestoneXvals = []
                milestoneLabels = []
                projectDeadlines = scenario.mrdTaskgroupDeadlines[project]
                for deadline in projectDeadlines[projectDeadlines.notna()]:
                    taskGroupIdx = projectDeadlines[projectDeadlines == deadline].index[0]
                    milestoneXvals.append(scenario.roadmapIdxToDateLut.index[scenario.roadmap.index == deadline][0])
                    milestoneLabels.append(scenario.mrdTaskgroups.loc[taskGroupIdx, TaskgroupColumnLabels.GROUNAME])

            # Milestone plotting dataframe to get the milestones nicely spaced
            self.plotParams[pltIdx]['milestoneTimeline'] = pd.DataFrame({
                'x':milestoneXvals,
                'lbl':milestoneLabels
            }).sort_values(by='x').reset_index(drop=True)
            self.plotParams[pltIdx]['milestoneTimeline']['y'] = np.tile(self.plotParams[pltIdx]['milestones'][project]['grid'], int(np.ceil(len(milestoneXvals)/stackedLabels)))[:len(milestoneXvals)]

            # Draw vertical lines for milestones
            axis.vlines(self.plotParams[pltIdx]['milestoneTimeline']['x'], self.plotParams[pltIdx]['ylim'][0], self.plotParams[pltIdx]['ylim'][1], color='white', linestyles='solid')  # White background line
            axis.vlines(self.plotParams[pltIdx]['milestoneTimeline']['x'], self.plotParams[pltIdx]['ylim'][0], self.plotParams[pltIdx]['ylim'][1], color=scenario.colordict[project], linestyles='dashed')  # Colour inidicator line.

            # Draw the milestones
            axis.scatter(self.plotParams[pltIdx]['milestoneTimeline']['x'], self.plotParams[pltIdx]['milestoneTimeline']['y'], marker="D", color=scenario.colordict[project]);

            # Draw Milestones labels on timeline
            for idx, milestone in self.plotParams[pltIdx]['milestoneTimeline'].iterrows():
                axis.annotate(milestone['lbl'],
                                    xy=(milestone['x'],self.plotParams[pltIdx]['milestones'][project]['grid'][idx % stackedLabels]),
                                    xytext=(3, np.sign(self.plotParams[pltIdx]['milestones'][project]['grid'][idx % stackedLabels])*3),
                                    textcoords="offset points", horizontalalignment="left",
                                    verticalalignment="center",
                                    fontsize=15)

        #milestoneLabels = [scenarioName + ": " + project for scenarioName, project in projectList]
        milestoneLabels = [project for scenarioName, project in projectList]
        axis.set_yticks(minor=False, ticks=[d['label'][1] for d in self.plotParams[pltIdx]['milestones'].values()] + list(range(0,math.ceil(scenario.maxResources.max(axis=0).max())+1,2)), labels=milestoneLabels + list(range(0,math.ceil(scenario.maxResources.max(axis=0).max())+1,2)), fontsize=15)
