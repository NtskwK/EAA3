import os
import json
from pathlib import Path
import random
from typing import List, Literal, Optional, Tuple

from PIL import Image

from maa.agent.agent_server import AgentServer, TaskDetail
from maa.custom_action import CustomAction
from maa.context import Context
from maa.define import RectType, Rect, RecognitionResult
from maa.pipeline import (
    JActionType,
    JInputText,
    JSwipe,
    JTarget,
    JOCR,
    JRecognitionType,
)

from utils.excel import get_values_from_excel
from utils.gui import select_path
from utils.config import get_config
from utils.logger import logger, log_dir
from utils import get_format_timestamp, smaller
from utils.item import item_keys, title_keys


def click(context: Context, x: int, y: int, w: int = 1, h: int = 1):
    return (
        context.tasker.controller.post_click(
            random.randint(x, x + w - 1), random.randint(y, y + h - 1)
        )
        .wait()
        .succeeded
    )


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


@AgentServer.custom_action("select_dataset_row")
class SelectDatasetRow(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        config = get_config()
        main_workbook_path = select_path(
            "请选择主工作簿文件",
            filters=[("Excel文件", "*.xlsx;*.xls"), ("所有文件", "*.*")],
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
        """
        :row_number: 数据行号
        :table_name: 数据表名
        """
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


def calc_inputbox(input: Rect, position: Literal["right", "bottom"]) -> Rect:
    box = Rect(input.x, input.y, input.w, input.h)
    if position == "right":
        box[0] = box[0] + int(2 * box[2])  # type: ignore
    elif position == "bottom":
        box[1] = box[1] + int(1.5 * box[3])  # type: ignore
    else:
        raise ValueError(f"Unknown position: {position}")
    return box


@AgentServer.custom_action("fill_program_name")
class FillProgramName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        box = calc_inputbox(argv.reco_detail.best_result.box, position="right")
        is_success = (
            context.tasker.controller.post_click(
                box[0] + box[2] // 2, box[1] + box[3] // 2
            )
            .wait()
            .succeeded
        )
        if not is_success:
            logger.error("点击输入框失败")
            return CustomAction.RunResult(success=False)

        config = get_config()
        prefix = "".join([str(config.get_value(key, "")) for key in title_keys])

        suffix = json.loads(argv.custom_action_param).get("suffix", "")
        program_name = f"{prefix}{suffix}"

        is_success = (
            context.tasker.controller.post_input_text(text=program_name)
            .wait()
            .succeeded
        )

        return CustomAction.RunResult(success=is_success)


@AgentServer.custom_action("click_right")
class ClickRight(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        box = calc_inputbox(argv.reco_detail.best_result.box, position="right")
        is_success = (
            context.tasker.controller.post_click(
                box[0] + box[2] // 2, box[1] + box[3] // 2
            )
            .wait()
            .succeeded
        )

        return CustomAction.RunResult(success=is_success)


@AgentServer.custom_action("input_value_from_config")
class InputValueFromConfig(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """
        :key: 配置中的数据键
        """
        key = json.loads(argv.custom_action_param).get("key", None)
        if key is None:
            logger.error("未配置数据键")
            return CustomAction.RunResult(success=False)

        config = get_config()
        value = config.get_value(key, None)
        if value is None:
            logger.error(f"未找到配置 {key}")
            return CustomAction.RunResult(success=False)

        return CustomAction.RunResult(
            success=context.tasker.controller.post_input_text(text=str(value))
            .wait()
            .succeeded
        )


@AgentServer.custom_action("fill_right_from_config")
class FillRightFromConfig(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        is_success = click(
            context, *calc_inputbox(argv.reco_detail.best_result.box, position="right")
        )
        if not is_success:
            logger.error("点击输入框失败")
            return CustomAction.RunResult(success=False)
        else:
            logger.info("点击输入框")

        key = json.loads(argv.custom_action_param).get("key", None)
        if key is None:
            logger.error("未配置数据键")
            return CustomAction.RunResult(success=False)

        config = get_config()
        value = config.get_value(key, None)
        if value is None:
            logger.error(f"未找到配置 {key}")
            return CustomAction.RunResult(success=False)
        is_success = (
            context.tasker.controller.post_input_text(text=str(value)).wait().succeeded
        )

        return CustomAction.RunResult(success=is_success)


@AgentServer.custom_action("fill_pz_zdmj")
class FillPzZdmj(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        config = get_config()
        zdmj_max = config.get_value("zdmj_max", None)
        if zdmj_max is None:
            logger.error("未配置最大宗地面积")
            return CustomAction.RunResult(success=False)

        zdmj = config.get_value("zdmj", None)
        if zdmj is None:
            logger.error("未配置宗地面积")
            return CustomAction.RunResult(success=False)

        try:
            value = smaller(zdmj_max, zdmj)
        except ValueError as e:
            logger.error(
                f"Error comparing values with smaller(zdmj_max={zdmj_max}, zdmj={zdmj}):{e}"
            )
            return CustomAction.RunResult(success=False)

        is_success = (
            context.tasker.controller.post_input_text(text=str(value)).wait().succeeded
        )

        return CustomAction.RunResult(success=is_success)


@AgentServer.custom_action("select_right_box")
class SelectRightBox(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        """
        :scroll: 向下滚动次数
        :target: 目标选项文本
        """
        param = json.loads(argv.custom_action_param)
        scroll = param.get("scroll", 0)
        target = param.get("target", None)
        if target is None:
            logger.error("未配置数据键或目标")
            return CustomAction.RunResult(success=False)

        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        rect_box = argv.reco_detail.best_result.box
        box = calc_inputbox(rect_box, position="right")
        click_position = (box[0] + box[2] // 2, box[1] + box[3] // 2)
        context.tasker.controller.post_click(*click_position).wait()
        logger.info("激活输入框")

        if scroll > 0:
            is_success = context.tasker.post_action(
                action_type=JActionType.Swipe,
                action_param=JSwipe(
                    only_hover=True, end=[box[0], box[1] + 50, box[2], box[3]]
                ),
            ).wait()
            if not is_success.succeeded:
                logger.error("滑动至选项框失败")
                return CustomAction.RunResult(success=False)

            for i in range(scroll):
                logger.info(f"滚动第{i+1}次")
                is_success = context.tasker.controller.post_scroll(0, -120).wait()
                if not is_success.succeeded:
                    logger.error("滚动列表失败")
                    return CustomAction.RunResult(success=False)

        context.tasker.controller.post_screencap().wait()
        img = context.tasker.controller.cached_image
        job = context.tasker.post_recognition(
            reco_type=JRecognitionType.OCR,
            reco_param=JOCR(expected=target),
            image=img,
        ).wait()
        detail = context.tasker.get_recognition_detail(job.job_id)
        if not detail or not detail.hit:
            logger.error("未识别到目标选项")
            return CustomAction.RunResult(success=False)

        # 计算label的右边界
        rect_right_edge = rect_box.x + rect_box.w
        results: List[RecognitionResult] = []
        for result in detail.filtered_results:
            # 只要位于label右侧的选项
            if result.box.x > rect_right_edge:
                results.append(result)

        if not results:
            logger.error("未找到位于输入框右侧的选项")
            return CustomAction.RunResult(success=False)

        best_result = results[0]
        is_success = click(context, *(best_result.box))

        return CustomAction.RunResult(success=is_success)


@AgentServer.custom_action("debug")
class DebugAction(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> CustomAction.RunResult:
        if not argv.reco_detail or not argv.reco_detail.best_result:
            logger.error("未提供识别结果，无法定位输入框")
            return CustomAction.RunResult(success=False)

        box = calc_inputbox(argv.reco_detail.best_result.box, position="right")
        context.tasker.controller.post_click(
            box[0] + box[2] // 2, box[1] + box[3] // 2
        ).wait()

        job = context.tasker.controller.post_input_text(
            text="Debug action executed."
        ).wait()

        if not job.succeeded:
            logger.error("执行输入文字动作失败")
            return CustomAction.RunResult(success=False)

        return CustomAction.RunResult(success=True)
