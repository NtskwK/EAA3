from maa.define import Rect
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import time
from numpy import ndarray, log

from utils.logger import logger


def get_senryoku(context: Context, image: ndarray, roi: list[int]) -> int | None:
    """
    获取战力
    """
    reco_detail = context.run_recognition(
        "GetSenryokuText",
        image,
        {
            "GetSenryokuText": {"roi": roi},
        },
    )

    if reco_detail is None or not reco_detail.hit:
        logger.debug(reco_detail)
        logger.warning("无法读取到战力！")
        return None

    source_text = str(reco_detail.best_result.text)  # type: ignore
    if source_text.endswith("万"):
        text = source_text[:-1]
        text += "0000"
    else:
        text = source_text

    if text.isdigit():
        logger.info(f"读取到战力：{source_text}")
        return int(text)

    logger.warning(f"战力解析错误：{source_text}")
    return None


@AgentServer.custom_recognition("FindToChallenge")
class FindToChallenge(CustomRecognition):
    """
    在积分赛中寻找可以挑战的对象
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        logger.info("尝试读取我方小队战力...")
        team_senryoku = get_senryoku(context, argv.image, [271, 337, 178, 29])
        if team_senryoku is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={},
            )

        enemy_roi_list = [
            [843, 236, 100, 30],
            [843, 352, 96, 31],
            [843, 472, 103, 27],
            [843, 589, 97, 29],
        ]

        logger.info("尝试读取敌方小队战力...")
        for idx, roi in enumerate(enemy_roi_list):
            enemySenryoku = get_senryoku(context, argv.image, roi)
            if enemySenryoku is None:
                logger.warning(f"无法读取到敌队{idx + 1}的战力！")
                return CustomRecognition.AnalyzeResult(
                    box=None,
                    detail={},
                )

            if enemySenryoku > team_senryoku:
                logger.warning(f"打不过敌队{idx + 1}!")
                continue

            logger.info(f"可以挑战敌队{idx + 1}!")
            reco_detail = context.run_recognition(
                "point_race_get_challenge_button",
                argv.image,
                {
                    "point_race_get_challenge_button": {
                        "index": idx,
                    }
                },
            )
            if reco_detail is None or not reco_detail.hit:
                logger.error(f"无法找到敌队{idx + 1}的挑战按钮！")
                return CustomRecognition.AnalyzeResult(
                    box=None,
                    detail={},
                )

            return CustomRecognition.AnalyzeResult(
                box=reco_detail.box,
                detail={},
            )

        logger.info(f"没一个打得过的，溜了溜了。")
        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={},
        )


@AgentServer.custom_recognition("FindPlantableFlower")
class FindPlantableFlower(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        flower_config = [
            (
                [400, 355, 111, 32],
                [440, 298, 37, 41],
            ),
            (
                [509, 355, 103, 29],
                [543, 298, 29, 27],
            ),
            (
                [607, 355, 106, 27],
                [642, 295, 34, 34],
            ),
            (
                [711, 355, 103, 32],
                [749, 300, 29, 29],
            ),
            (
                [810, 256, 143, 140],
                [844, 298, 37, 34],
            ),
        ]

        logger.info("开始检测可种植的花(需10个种子)...")

        # 遍历5种花,依次检查种子数量
        for flower_idx, (seed_roi, btn_roi) in enumerate(flower_config):
            flower_num = flower_idx + 1
            logger.info(f"正在检查第{flower_num}种花...")

            current_seeds = self.get_seed_count(
                context=context, image=argv.image, roi=seed_roi
            )
            if current_seeds is None:
                logger.warning(f"第{flower_num}种花:种子数量读取失败,跳过")
                continue

            # 判断种子是否足够(≥10)
            if current_seeds < 10:
                logger.info(f"第{flower_num}种花:种子不足({current_seeds}/10),跳过")
                continue

            # 种子充足,返回按钮位置
            logger.info(f"第{flower_num}种花:种子充足({current_seeds}/10)")
            btn_box = Rect(btn_roi[0], btn_roi[1], btn_roi[2], btn_roi[3])
            return CustomRecognition.AnalyzeResult(
                box=btn_box,
                detail={
                    "flower_num": flower_num,
                    "seed_count": current_seeds,
                    "btn_roi": btn_roi,
                },
            )

        # 无可用种子或全识别失败
        invalid_box = Rect(
            0, 0, 1, 1
        )  # 直接返回None的box会重试，所以我返回一个不影响的box
        return CustomRecognition.AnalyzeResult(
            box=invalid_box, detail={"has_valid_target": False}
        )

    def get_seed_count(
        self, context: Context, image: ndarray, roi: list[int]
    ) -> int | None:
        """
        在选花界面中寻找可以种的花
        """

        reco_detail = context.run_recognition(
            "GetSenryokuText",
            image,
            {
                "GetSenryokuText": {"roi": roi},
            },
        )

        if reco_detail is None:
            logger.warning(f"ROI{roi}:种子数量识别失败(识别器返回None)")
            return None

        if not reco_detail.hit:
            logger.debug(f"ROI{roi}:未识别到种子文本(hit=False)")
            logger.warning(f"ROI{roi}:无法读取到种子数量文本!")
            return None

        if reco_detail.best_result is None:
            logger.warning(f"ROI{roi}:识别到文本但解析失败(best_result为空)")
            return None

        source_text = str(reco_detail.best_result.text).strip().replace(" ", "")  # type: ignore
        logger.debug(f"ROI{roi}:识别到种子文本:{source_text}")

        prefix = "剩余"
        if prefix not in source_text:
            logger.warning(f"ROI{roi}:种子文本无'剩余'关键字,识别文本:{source_text}")
            return None

        colon_index = source_text.find(prefix) + len(prefix)
        if colon_index >= len(source_text) or source_text[colon_index] not in [
            ":",
            "：",
        ]:
            logger.warning(
                f"ROI{roi}:种子文本格式错误(无有效冒号),识别文本:{source_text}"
            )
            return None

        slash_index = source_text.find("/", colon_index + 1)
        if slash_index == -1:
            logger.warning(f"ROI{roi}:种子文本无'/'分隔符,识别文本:{source_text}")
            return None

        seed_str = source_text[colon_index + 1 : slash_index]
        if not seed_str.isdigit():
            logger.warning(
                f"ROI{roi}:种子数量不是数字,实际:{seed_str}(识别文本:{source_text})"
            )
            return None

        current_seeds = int(seed_str)
        logger.info(f"ROI{roi}:解析到种子数量:{current_seeds}/10")
        return current_seeds
