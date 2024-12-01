# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import pandas as pd
import datetime as dt
import numpy as np

from projplan.timehandling import Timeline
from projplan import ColumnLabelSpecifiers

class Constraint(object):
    def __init__(self, start: dt.datetime | None, end: dt.datetime | None, value: float):
        self.start = start
        self.end   = end
        self.value = value

    @staticmethod
    def infiniteStart() -> dt.datetime:
        return dt.datetime(year=1,month=1,day=1)

    @staticmethod
    def infiniteEnd() -> dt.datetime:
        return dt.datetime(year=9999,month=12,day=31)

    @property
    def start(self) -> dt.datetime:
        if self._start is not None:
            return self._start
        else:
            return Constraint.infiniteStart()

    @start.setter
    def start(self, value: dt.datetime) -> None:
        if type(value) is dt.datetime:
            self._start = value
        elif type(value) is dt.date:
            self._start = dt.datetime.combine(value, dt.time(hour=0,minute=0,second=0))
        else:
            self._start = None

    @property
    def end(self) -> dt.datetime:
        if self._end is not None:
            return self._end
        else:
            return Constraint.infiniteEnd()

    @end.setter
    def end(self, value: dt.datetime | dt.date) -> None:
        if type(value) is dt.datetime:
            self._end = value
        elif type(value) is dt.date:
            self._end = dt.datetime.combine(value, dt.time(hour=0,minute=0,second=0))
        else:
            self._end = None

class ResourcePool(Timeline):
    """TODO PMi"""
    RESOURCES_COLUMN_LABEL         = 'resources'
    EFFICIENCY_COLUMN_LABEL        = 'efficiency'
    PARALLELIZABILITY_COLUMN_LABEL = 'parallelizability'

    def __init__(self, *args, **kwargs) -> None:
        """Initialize a resource pool
        A resource pool are resources that can be used by a specific set of taks the team is working
        on, which can either be something generic like customer support, or a specific project.

        Parameters
        ----------
        name                   : Name of the resource pool as string, defaults to "General".
        resources              : Resources allocated in this pool as list of tuples(start, end, resource) or constant, i.e. list[tuple[dt.datetime | None,dt.datetime | None,float]] | float. None if no resources can be used for scheduling.
        allocateFreeResources  : Boolean, true if the resource pool can allocate free resources within a scenario (get more resources than defined in resources), defaults to false.
        yieldUnusedResources   : Boolean, true if the resource pool can yield unused resources within a scenario (get more resources than defined in resources), defaults to false.
        color                  : Plotting colour for this focus area.
        timelineStart          : Timeline start date as str or datetime.date, defaults to 1945-07-01.
        timelineEnd            : Timeline end date as str or datetime.date, defaults to today plus five years.
        efficiency             : Amount of work that can be done per task and timestep, defaults to 1.
        """
        super(ResourcePool, self).__init__(*args, **kwargs)
        self._defaultParameter = {ResourcePool.EFFICIENCY_COLUMN_LABEL:        kwargs.pop('defaultEfficiency', 1.0),
                                  ResourcePool.RESOURCES_COLUMN_LABEL:         kwargs.pop('defaultResources',  0.0),
                                  ResourcePool.PARALLELIZABILITY_COLUMN_LABEL: kwargs.pop('defaultParallelizability', -1.0)}
        self._initkwargs = kwargs

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Name of the resource pool"""
        return self._initkwargs.get('name', 'General')

    @property
    def label(self) -> str:
        """Name of the scenario"""
        if not hasattr(self, '_label'):
            self._label = self._initkwargs.pop('label', self.name)
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        self._label = value

    @property
    def nameConstraint(self) -> str:
        return self.name + '-' + ColumnLabelSpecifiers.CONSTRAINTINDICATOR

    @property
    def namePriority(self) -> str:
        return self.name + '-' + ColumnLabelSpecifiers.PRIORITYINDICATOR

    @property
    def nameDeadline(self) -> str:
        return self.name + '-' + ColumnLabelSpecifiers.DEADLINEINDICATOR

    @property
    def allocateFreeResources(self) -> bool:
        return self._initkwargs.get('allocateFreeResources', False)

    @property
    def yieldUnusedResources(self) -> bool:
        return self._initkwargs.get('yieldUnusedResources', False)

    @property
    def color(self) -> str:
        return self._initkwargs.get('color', '#000000')

    @property
    def parameters(self) -> pd.DataFrame:
        if hasattr(self, '_parameters'):
            doUpdate = ((self._parameters.index[0] != self._timelineStart.asPdTimestamp) or (self._parameters.index[-1] != self._timelineEnd.asPdTimestamp))
        else:
            doUpdate = True
        if doUpdate:
            self._parameters = pd.DataFrame({ResourcePool.EFFICIENCY_COLUMN_LABEL:        np.full(self.timeline.shape, np.nan),
                                             ResourcePool.RESOURCES_COLUMN_LABEL:         np.full(self.timeline.shape, np.nan),
                                             ResourcePool.PARALLELIZABILITY_COLUMN_LABEL: np.full(self.timeline.shape, np.nan)}, index=self.timeline)
            initParams = self._initkwargs.get('initParams', None)
            if initParams is not None:
                constraints = {ResourcePool.EFFICIENCY_COLUMN_LABEL: [], ResourcePool.RESOURCES_COLUMN_LABEL: [], ResourcePool.PARALLELIZABILITY_COLUMN_LABEL: []}
                if type(initParams) is float or type(initParams) is int:
                    constraints[ResourcePool.EFFICIENCY_COLUMN_LABEL].append(Constraint(None, None, self._defaultParameter[ResourcePool.EFFICIENCY_COLUMN_LABEL]))
                    constraints[ResourcePool.RESOURCES_COLUMN_LABEL].append(Constraint(None, None, initParams))
                    constraints[ResourcePool.PARALLELIZABILITY_COLUMN_LABEL].append(Constraint(None, None, self._defaultParameter[ResourcePool.PARALLELIZABILITY_COLUMN_LABEL]))
                elif type(initParams) is list:
                    for (start, end, efficency, resources, parallelizability) in initParams:
                        constraints[ResourcePool.EFFICIENCY_COLUMN_LABEL].append(Constraint(start, end, efficency))
                        constraints[ResourcePool.RESOURCES_COLUMN_LABEL].append(Constraint(start, end, resources))
                        constraints[ResourcePool.PARALLELIZABILITY_COLUMN_LABEL].append(Constraint(start, end, parallelizability))
                for column in [ResourcePool.EFFICIENCY_COLUMN_LABEL, ResourcePool.RESOURCES_COLUMN_LABEL, ResourcePool.PARALLELIZABILITY_COLUMN_LABEL]:
                    for constraint in constraints[column]:
                        self._parameters.loc[(self._parameters.index >= constraint.start) & (self._parameters.index <= constraint.end), column] = constraint.value
                    self._parameters.loc[:,column] = self._parameters.loc[:,column].ffill()
                    self._parameters.loc[:,column] = self._parameters.loc[:,column].bfill()
        return self._parameters
