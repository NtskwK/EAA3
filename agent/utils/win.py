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
import win32gui


def resize_window_by_title(title_keyword, width=1200, height=900):
    hwnd_target = None

    def callback(hwnd, extra):
        nonlocal hwnd_target
        if win32gui.GetWindowText(hwnd).find(title_keyword) != -1:
            hwnd_target = hwnd
            return False
        return True

    win32gui.EnumWindows(callback, None)

    if hwnd_target:
        # 调整窗口位置（0,0 为左上角）和大小，立即重绘
        win32gui.MoveWindow(hwnd_target, 0, 0, width, height, True)
        print(f"窗口已设为 {width}×{height}")
        return True
    else:
        print("未找到目标窗口")
        return False
