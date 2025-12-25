import os
import json
from pathlib import Path
import random
from typing import List, Literal, Optional, Tuple

from PIL import Image

from maa.agent.agent_server import AgentServer, TaskDetail
from maa.custom_action import CustomAction
from maa.context import Context
from maa.define import RectType, Rect
from maa.pipeline import JActionType, JInputText

from utils.excel import get_values_from_excel
from utils.gui import select_path
from utils.config import get_config
from utils.logger import logger, log_dir
from utils import get_format_timestamp
from utils.item import item_keys


def click(context: Context, x: int, y: int, w: int = 1, h: int = 1):
    context.tasker.controller.post_click(
        random.randint(x, x + w - 1), random.randint(y, y + h - 1)
    ).wait()


@AgentServer.custom_action("MyAction111")
class MyAction111(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        logger.info("MyAction111 is running!")

        # 监听任务停止信号以提前终止任务
        # 相当于用户按下了“停止”按钮
        if context.tasker.stopping:
            logger.info("Task is stopping, exiting MyAction111 early.")
            return CustomAction.RunResult(success=False)

        # 执行自定义任务
        # ...

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("Screenshot")
class Screenshot(CustomAction):
    """
    自定义截图动作，保存当前屏幕截图到指定目录。

    参数格式:
    {
        "save_dir": "保存截图的目录路径"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:

        # image array(BGR)
        screen_array = context.tasker.controller.cached_image

        # Check resolution aspect ratio
        height, width = screen_array.shape[:2]
        aspect_ratio = width / height
        target_ratio = 16 / 9
        # Allow small deviation (within 1%)
        if abs(aspect_ratio - target_ratio) / target_ratio > 0.01:
            logger.error(f"当前模拟器分辨率不是16:9! 当前分辨率: {width}x{height}")

        # BGR2RGB
        if len(screen_array.shape) == 3 and screen_array.shape[2] == 3:
            rgb_array = screen_array[:, :, ::-1]
        else:
            rgb_array = screen_array
            logger.warning("当前截图并非三通道")

        img = Image.fromarray(rgb_array)

        save_dir = log_dir
        os.makedirs(save_dir, exist_ok=True)
        time_str = get_format_timestamp()
        img.save(f"{save_dir}/{time_str}.png")
        logger.info(f"截图保存至 {save_dir}/{time_str}.png")

        task_detail: TaskDetail = context.tasker.get_task_detail(
            argv.task_detail.task_id
        )  # type: ignore
        logger.debug(
            f"task_id: {task_detail.task_id}, task_entry: {task_detail.entry}, status: {task_detail.status._status}"
        )

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("GoIntoEntry")
class GoIntoEntry(CustomAction):
    """
    从主界面获取功能入口
    参数:
    {
        "template": "功能入口的匹配模板"
    }
    """

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        target = json.loads(argv.custom_action_param).get("template", "")
        if not isinstance(target, str) and not isinstance(target, list):
            logger.error(f"目标格式错误: {target}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)
        # 检查目标是否为空字符串或空列表
        if (isinstance(target, str) and not target.strip()) or (
            isinstance(target, list) and len(target) == 0
        ):
            logger.error(f"目标为空: {target}")
            context.tasker.post_stop()
            return CustomAction.RunResult(success=False)

        found, box = self.rec_entry(context, target)
        if found and box is not None:
            logger.info("识别到功能入口")
            click(context, *box)
            return CustomAction.RunResult(success=True)

        if context.tasker.stopping:
            logger.info("任务停止，提前退出")
            return CustomAction.RunResult(success=False)

        # 右滑两次
        for i in range(2):
            logger.info(f"右滑第{i+1}次")
            context.run_task("main_screen_swipe_to_right")
            context.tasker.controller.post_screencap().wait()
            found, box = self.rec_entry(context, target)
            if found and box is not None:
                logger.info("识别到功能入口")
                click(context, *box)
                return CustomAction.RunResult(success=True)
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

        # 左滑两次
        for i in range(2):
            logger.info(f"左滑第{i+1}次")
            context.run_task("main_screen_swipe_to_left")
            context.tasker.controller.post_screencap().wait()
            found, box = self.rec_entry(context, target)
            if found and box is not None:
                logger.info("识别到功能入口")
                click(context, *box)
                return CustomAction.RunResult(success=True)
            if context.tasker.stopping:
                logger.info("任务停止，提前退出")
                return CustomAction.RunResult(success=False)

        logger.error("获取功能入口失败")
        return CustomAction.RunResult(success=False)

    def rec_entry(
        self, context: Context, template: str | list[str]
    ) -> Tuple[bool, Optional[RectType]]:
        reco_detail = context.run_recognition(
            "click_entry",
            context.tasker.controller.cached_image,
            {
                "click_entry": {
                    "recognition": {
                        "param": {
                            "template": template,
                        }
                    }
                },
            },
        )
        if reco_detail is None or not reco_detail.hit:
            logger.info("未识别到功能入口")
            return False, None

        if reco_detail.best_result is None:
            logger.warning("识别到功能入口但解析失败(best_result为空)")
            return False, None

        return True, reco_detail.best_result.box


@AgentServer.custom_action("select_dataset_row")
class SelectDatasetRow(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        config = get_config()
        main_workbook_path = select_path(
            "请选择主工作簿文件", filters="Excel文件 (*.xlsx;*.xls)|*.xlsx;*.xls"
        )
        housePlan_dir = select_path("请选择户型图文件夹", is_dir=True)
        estatePlan_dir = select_path("请选择宗地图文件夹", is_dir=True)
        familyMember_dir = select_path("请选择家庭成员信息文件夹", is_dir=True)
        for path in [
            main_workbook_path,
            housePlan_dir,
            estatePlan_dir,
            familyMember_dir,
        ]:
            if (path is None) or (not path.exists()):
                logger.error(f"路径无效: {path}")
                return CustomAction.RunResult(success=False)
        path_details = [
            ("main_workbook_path", str(main_workbook_path)),
            ("housePlan_dir", str(housePlan_dir)),
            ("estatePlan_dir", str(estatePlan_dir)),
            ("familyMember_dir", str(familyMember_dir)),
        ]
        for key, path in path_details:
            config.set_value(key, path)
            logger.info(f"已设置 {key} 为 {path}")

        param = json.loads(argv.custom_action_param)
        keys = ["row_number", "table_name", "region"]
        for key in keys:
            if not key in param:
                logger.error(f"参数缺失: {key}")
                return CustomAction.RunResult(success=False)

            config.set_value(key, param[key])
            logger.info(f"已设置 {key} 为 {param[key]}")

        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("load_data_detail")
class LoadDataDetail(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        config = get_config()
        row_number = config.get_value("row_number", None)
        table_name = config.get_value("table_name", None)
        if row_number is None or table_name is None:
            logger.error("未配置行号或表名")
            return CustomAction.RunResult(success=False)

        logger.info(f"正在加载 行号: {row_number}, 表名: {table_name}")
        param = json.loads(argv.custom_action_param)

        row = {}
        column_names = []
        for key in item_keys:
            v = param.get(key, None)
            if v is None:
                logger.error(f"参数缺失: {key}")
                return CustomAction.RunResult(success=False)
            logger.info(f"已加载 {key}: {v}")
            column_names.append(v)

        data_array = get_values_from_excel(
            str(config.get_value("main_workbook_path", "")),
            table_name,
            row_number,
            column_names,
        )
        for k, v in zip(item_keys, data_array):
            if v is None:
                logger.error(f"数据缺失: {k}")
                return CustomAction.RunResult(success=False)
            row[k] = v
            logger.info(f"已读取 {k}: {v}")

        config.set_value("current_data_row", row)

        return CustomAction.RunResult(success=True)


def calc_inputbox(box: Rect, position: Literal["right", "bottom"]) -> Rect:
    if position == "right":
        box.x = box.x + int(1.5 * box.w)
    elif position == "bottom":
        box.y = box.y + int(1.5 * box.h)
    else:
        raise ValueError(f"Unknown position: {position}")
    return box


@AgentServer.custom_action("fill_estate_survey_project_name")
class FillEstateSurveyProjectName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        config = get_config()
        project_name = config.get_value("estate_survey_project_name", None)
        if project_name is None:
            logger.error("未配置项目名称")
            return CustomAction.RunResult(success=False)

        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        is_success = (
            context.tasker.post_action(
                action_type=JActionType.InputText,
                action_param=JInputText(input_text=project_name),
                box=calc_inputbox(argv.reco_detail.best_result.box, position="right"),
            )
            .wait()
            .succeeded
        )

        return CustomAction.RunResult(success=is_success)
