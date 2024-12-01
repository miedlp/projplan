# Copyright (c) 2023-2024 METTLER TOLEDO
# Copyright (c) 2024 Philipp Miedl
#
# SPDX-License-Identifier: EUPL-1.2

import pandas as pd
import datetime as dt

class Datehandler(object):
    def __init__(self, date):
        self._date = self._convertTimeToStoreValue(date)
        pass

    def _convertTimeToStoreValue(self, value):
        if (type(value) == dt.datetime) or (type(value) == pd.Timestamp):
            return value.strftime('%Y-%m-%d')
        elif type(value) == str:
            return value

    def __str__(self) -> str:
        return self._date

    @property
    def asStr(self) -> str:
        return self._date

    @property
    def asDtDatetime(self) -> dt.datetime:
        return dt.datetime.strptime(self.date, '%Y-%m-%d')

    @property
    def asPdTimestamp(self) -> pd.Timestamp:
        return pd.Timestamp(self._date)

class Timeline(object):
    def __init__(self, *args, **kwargs) -> None:
        self.timelineStart = kwargs.pop('timelineStart', '1945-07-01')
        self.timelineEnd   = kwargs.pop('timelineEnd', (pd.to_datetime('today').normalize()+pd.DateOffset(years=5)))
    
    @property
    def timeline(self) -> pd.date_range:
        return pd.date_range(start=self._timelineStart.asPdTimestamp, end=self._timelineEnd.asPdTimestamp, freq='D', unit='s')

    @property
    def timelineLut(self) -> pd.DataFrame:
        return pd.DataFrame(self.timeline)

    @property
    def timelineStart(self) -> str:
        if not hasattr(self, '_timelineStart'):
            self._timelineStart = Datehandler('1945-07-01')
        return self._timelineStart.asStr

    @timelineStart.setter
    def timelineStart(self, value: str | dt.datetime | pd.Timestamp) -> None:
        self._timelineStart = Datehandler(value)

    @property
    def timelineEnd(self) -> str:
        if not hasattr(self, '_timelineEnd'):
            self._timelineEnd = Datehandler(pd.to_datetime('today').normalize()+pd.DateOffset(years=5))
        return self._timelineEnd.asStr

    @timelineEnd.setter
    def timelineEnd(self, value: str | dt.datetime | pd.Timestamp) -> None:
        self._timelineEnd = Datehandler(value)

