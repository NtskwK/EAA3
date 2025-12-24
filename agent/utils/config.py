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
from pathlib import Path
import json

from .pathbase import project_root


class Config:
    config_file = Path(project_root) / "config" / "config.json"
    detail: dict = {}

    def __init__(self):
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.detail = json.load(f)
            for key in self.detail:
                self.detail[key] = self.detail[key]
                setattr(self, key, self.detail[key])

    def get_value(self, key: str, default=None):
        return self.detail.get(key, default)

    def set_value(self, key: str, value):
        self.detail[key] = value
        setattr(self, key, value)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.detail, f, ensure_ascii=False, indent=4)
