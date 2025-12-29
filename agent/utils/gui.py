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
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from typing import List


def select_path(
    title: str,
    filters: List[tuple[str, str]] | None = None,
    is_dir: bool = False,
) -> Path | None:
    root = tk.Tk()
    root.withdraw()
    # 确保窗口在最前面
    root.attributes("-topmost", True)

    if is_dir:
        path = filedialog.askdirectory(title=title)
    else:
        if filters is None:
            filters = [("All Files", "*.*")]
        path = filedialog.askopenfilename(title=title, filetypes=filters)

    root.destroy()

    if path:
        return Path(path)

    return None


def select_directory(title: str) -> Path | None:
    return select_path(title, is_dir=True)


def dialog_yes_or_no(title: str, message: str) -> bool:
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口，只显示对话框

    # 弹出确认对话框
    result = messagebox.askyesno(title=title, message=message)  # 对话框标题  # 提示内容

    return result


if __name__ == "__main__":
    # 简单测试
    print(f"Selected file: {select_path('请选择一个文件')}")
    print(f"Selected directory: {select_directory('请选择一个目录')}")
    print(
        f"User confirmed: {dialog_yes_or_no('确认操作', """
您确定要执行此操作吗？
你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？你知道你正在在做什么吗？
    """)}"
    )
