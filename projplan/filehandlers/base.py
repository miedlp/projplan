# Copyright (c) 2023-2024 METTLER TOLEDO
#
# SPDX-License-Identifier: EUPL-1.2

import pathlib as pl
import pandas as pd

class filehandlers():
    @staticmethod
    def getDataFileEnding() -> str:
        return ''

    @staticmethod
    def readPlanningFile(filepath: pl.Path) -> pd.DataFrame:
        raise Exception("This backend cannot be used to read the mapping file.")

