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

# 计算项目根目录的绝对路径（基于此脚本的位置）
from pathlib import Path


_current_file = Path(__file__).resolve()
_utils_dir = _current_file.parent  # utils 目录
_agent_dir = _utils_dir.parent  # agent 目录
project_root = _agent_dir.parent  # 项目根目录
