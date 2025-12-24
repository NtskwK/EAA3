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
import wx


def select_file(
    title: str, filters: str | None = None, is_dir: bool = False
) -> Path | None:
    app = wx.GetApp() or wx.App(False)

    if is_dir:
        with wx.DirDialog(
            None, title, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                return Path(dialog.GetPath())
    else:
        if filters is None:
            filters = "All files (*.*)|*.*"
        with wx.FileDialog(
            None, title, wildcard=filters, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                return Path(dialog.GetPath())

    return None


def select_directory(title: str) -> Path | None:
    return select_file(title, is_dir=True)


if __name__ == "__main__":
    # 简单测试
    print(f"Selected file: {select_file('请选择一个文件')}")
    print(f"Selected directory: {select_directory('请选择一个目录')}")
