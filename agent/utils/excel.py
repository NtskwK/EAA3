# Copyright (C) 2025 ntskwk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import List
import openpyxl
import csv


def get_values_from_excel(
    file_path: str, sheet_name: str, row: int, columns: List[str]
) -> list:
    workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
    sheet = workbook[sheet_name]
    values = []
    for col in columns:
        cell = sheet[f"{col}{row}"]
        if cell.value is None:
            values.append("")
        else:
            values.append(str(cell.value))

    return values
