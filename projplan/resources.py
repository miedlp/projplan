# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import pandas as pd
import datetime as dt
import numpy as np

from projplan.timehandling import Timeline
from projplan.filehandlers import InputFileStandardLabels

class Constraint():
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
    RESOURCES_COLUMN_LABEL = 'Resources'
    BASECOST_COLUMN_LABEL  = 'Basecost'
    EFFICIENCY_COLUMN_LABEL = 'Efficiency '

    def __init__(self, **kwargs) -> None:
        """Initialize a resource pool
        A resource pool are resources that can be used by a specific set of taks the team is working
        on, which can either be something generic like customer support, or a specific project.

        Parameters
        ----------
        name                   : Name of the resource pool as string, defaults to "General".
        basecost               : Base cost caused by this resource pool if not task is scheduled as integer or float, defaults to 0.
        resources              : Resources allocated in this pool as list of tuples(start, end, resource) or constant, i.e. list[tuple[dt.datetime | None,dt.datetime | None,float]] | float. None if no resources can be used for scheduling.
        allocateFreeResources  : Boolean, true if the resource pool can allocate free resources within a scenario (get more resources than defined in resources), defaults to false.
        yieldUnusedResources   : Boolean, true if the resource pool can yield unused resources within a scenario (get more resources than defined in resources), defaults to false.
        color                  : Plotting colour for this focus area.
        timelineStart     : Timeline start date as str or datetime.date, defaults to 1945-07-01.
        timelineEnd       : Timeline end date as str or datetime.date, defaults to today plus five years.
        efficiency        : Amount of work that can be done per task and timestep, defaults to 1.
        """
        if 'timelineStart' in kwargs:
            self.timelineStart = kwargs.pop('timelineStart')
        if 'timelineEnd' in kwargs:
            self.timelineEnd = kwargs.pop('timelineEnd')
        for key in kwargs:
            setattr(self, '_' + key, kwargs[key])

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Name of the resource pool"""
        if not hasattr(self, '_name'):
          self._name= 'General'
        return self._name

    @property
    def constraintColumnName(self) -> str:
        return self.name + InputFileStandardLabels.CONSTRAINTINDICATOR

    def _shouldUpdateTimeline(self, timelineName):
        if not hasattr(self, timelineName):
            return True
        timeline = getattr(self, timelineName)
        if ((timeline.index[0] != self._timelineStart.asPdTimestamp) or (timeline.index[-1] != self._timelineEnd.asPdTimestamp)):
            return True
        return False

    @property
    def efficiency (self) -> float | int:
        if self._shouldUpdateTimeline('_efficiency Timeline'):
            self._efficiencyTimeline = self._generateTimeline(getattr(self, '_efficiency ', 1), ResourcePool.EFFICIENCY_COLUMN_LABEL)
        return self._efficiencyTimeline

    @property
    def basecost(self) -> pd.DataFrame:
        if self._shouldUpdateTimeline('_basecostTimeline'):
            self._basecostTimeline = self._generateTimeline(getattr(self, '_basecost', 0), ResourcePool.BASECOST_COLUMN_LABEL)
        return self._basecostTimeline

    @property
    def resources(self) -> pd.DataFrame:
        if self._shouldUpdateTimeline('_resourcesTimeline'):
            self._resourcesTimeline = self._generateTimeline(getattr(self, '_resources', 0), ResourcePool.RESOURCES_COLUMN_LABEL)
        return self._resourcesTimeline

    def _generateTimeline(self, value: list[tuple[dt.datetime | None,dt.datetime | None,float]] | float, columnName: str) -> None:
        if type(value) is list:
            constraints = []
            for (start, end, val) in value:
                constraints.append(Constraint(start, end, val))
        else:
            constraints   = [Constraint(None, None, value)]
        timelineIdx = self.timeline
        timeline = pd.DataFrame({columnName: np.full(timelineIdx.shape, np.nan)}, index=timelineIdx)
        for constraint in constraints:
            timeline.loc[(timeline.index >= constraint.start) & (timeline.index <= constraint.end)] = constraint.value
        timeline = timeline.ffill()
        timeline = timeline.bfill()
        return timeline

    @property
    def allocateFreeResources(self) -> bool:
        return getattr(self, '_allocateFreeResources', False)

    @property
    def color(self) -> str:
        return getattr(self, '_color', '#000000')
