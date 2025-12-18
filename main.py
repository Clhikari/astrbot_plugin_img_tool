import base64
from astrbot.api.all import AstrMessageEvent
from astrbot.api.star import register, Star, Context
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
import aiohttp
from pydantic import Field
from pydantic.dataclasses import dataclass
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool
from astrbot.core.astr_agent_context import AstrAgentContext


@dataclass
class DoubaoDrawTool(FunctionTool[AstrAgentContext]):
    name: str = "draw_image_doubao"
    description: str = (
        "【文生图】使用豆包模型从零绘制/生成一张新图片。当用户想要'画'或'生成'一张不存在的图时使用此工具。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "画面描述"},
            },
            "required": ["prompt"],
        }
    )
    plugin_instance: object = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        """执行图片生成"""
        prompt = kwargs.get("prompt", "")

        if not prompt:
            yield logger.warning("缺少图片描述")
            return

        event = context.context.event
        event: AstrMessageEvent
        event.plain_result("🎨 正在生成图片...")

        # API 请求
        url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.plugin_instance.config['volc_api_key']}",
        }
        data = {
            "model": self.plugin_instance.config["volc_endpoint_id"],
            "prompt": prompt,
        }

        image_url = ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(
                            f"API 请求失败，状态码: {resp.status}, 错误: {error_text}"
                        )
                        yield event.plain_result(f"❌ API请求失败: {error_text}")
                        return
                    result = await resp.json()

                    if "data" in result and len(result["data"]) > 0:
                        image_url = result["data"][0].get("url")
                    else:
                        logger.error(f"API返回结构异常: {result}")

        except Exception as e:
            logger.error(f"生成过程中发生异常：{str(e)}")
            yield event.plain_result(f"❌ 生成失败: {str(e)}")
            return

        # 发送图片
        if image_url:
            chain = [
                Comp.At(qq=event.get_sender_id()),
                Comp.Plain("✨ 绘制完成：\n"),
                Comp.Image.fromURL(image_url),
            ]
            yield event.chain_result(chain)
            logger.info(f"图片已生成并发送: {image_url}")
        else:
            logger.warning("未能解析出有效的图片 URL")
            yield event.plain_result("❌ 生成失败，未获取到图片 URL")


@dataclass
class QwenEditTool(FunctionTool[AstrAgentContext]):
    name: str = "edit_image_qwen"
    description: str = (
        "【修图/改图】使用Qwen模型修改用户发送的图片。当用户想要'把xx改成xx'、'换衣服'、'修图'时使用此工具。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "修改指令，例如'把红色改成蓝色'",
                },
            },
            "required": ["instruction"],
        }
    )
    plugin_instance: object = None

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs):
        instruction = kwargs.get("instruction", "")
        logger.info(f"修图指令: {instruction}")
        event = context.context.event
        event: AstrMessageEvent

        # 找图并转Base64
        base64_image = await self._get_user_image_base64(event)
        if not base64_image:
            yield event.plain_result("❌ 请先发送一张图片，再说出修图指令。")
            return

        yield event.plain_result("🎨 正在高清修图中，请稍候...")

        # 获取配置
        config = self.plugin_instance.config
        size = config.get("edit_image_size", "1536*1536")
        enable_neg = config.get("enable_negative_prompt", True)
        neg_prompt = config.get("negative_prompt", "低质量，低分辨率")

        # 调用阿里云API - 同步模式
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['aliyun_api_key']}",
        }

        # 构建参数
        params = {
            "n": 1,
            "prompt_extend": True,
            "watermark": False,
            "size": size,
        }

        # 根据配置决定是否添加负面提示词
        if enable_neg and neg_prompt:
            params["negative_prompt"] = neg_prompt

        payload = {
            "model": "qwen-image-edit-plus-2025-10-30",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": base64_image},
                            {"text": instruction},
                        ],
                    }
                ]
            },
            "parameters": params,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"阿里云API报错: {err}")
                        yield event.plain_result(f"❌ API报错: {err}")
                        return

                    result = await resp.json()

                    if "output" in result and "choices" in result["output"]:
                        content = result["output"]["choices"][0]["message"]["content"]
                        final_img = next(
                            (item["image"] for item in content if "image" in item),
                            None,
                        )

                        if final_img:
                            yield event.chain_result(
                                [
                                    Comp.At(qq=event.get_sender_id()),
                                    Comp.Plain("✨ 修图完成：\n"),
                                    Comp.Image.fromURL(final_img),
                                ]
                            )
                            logger.info(f"修图成功，输出分辨率: {size}")
                        else:
                            yield event.plain_result("❌ 未能获取到修改后的图片")
                    else:
                        logger.error(f"API返回异常: {result}")
                        yield event.plain_result(f"❌ API返回异常")

        except Exception as e:
            logger.error(f"修图异常: {e}")
            yield event.plain_result(f"❌ 异常: {e}")

    async def _get_user_image_base64(self, event) -> str | None:
        """获取图片并转换为Base64"""
        for component in event.message_obj.message:
            if isinstance(component, Comp.Image):
                url = component.url
                logger.info(f"原始图片URL: {url}")

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                logger.error(f"图片下载失败: {resp.status}")
                                return None

                            image_data = await resp.read()
                            encoded = base64.b64encode(image_data).decode("utf-8")

                            # 判断图片格式
                            if image_data[:4] == b"\x89PNG":
                                content_type = "image/png"
                            elif image_data[:2] in (b"\xff\xd8", b"\xff\xdb"):
                                content_type = "image/jpeg"
                            elif (
                                image_data[:4] == b"RIFF"
                                and image_data[8:12] == b"WEBP"
                            ):
                                content_type = "image/webp"
                            else:
                                content_type = resp.headers.get(
                                    "Content-Type", "image/jpeg"
                                )

                            base64_image = f"data:{content_type};base64,{encoded}"
                            logger.info(f"✅ 图片已转换 (类型: {content_type})")
                            return base64_image

                except Exception as e:
                    logger.error(f"图片处理失败: {e}")
                    return None
        return None


@register(
    "AIImagePlugin",
    "Clhikari",
    "AI图片生成与编辑工具",
    "1.0.0",
    "https://github.com/Clhikari/astrbot_plugin_img_tool",
)
class AIImagePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 检查配置完整性
        required_keys = ["volc_api_key", "volc_endpoint_id", "aliyun_api_key"]
        missing_keys = [key for key in required_keys if not config.get(key)]

        if missing_keys:
            logger.warning(f"⚠️ 缺少配置项: {', '.join(missing_keys)}")
            logger.warning("请在 WebUI 的插件管理页面配置相关 API Key")
        else:
            logger.info("✅ 配置加载成功")

        # 注册工具
        doubao_tool = DoubaoDrawTool()
        doubao_tool.plugin_instance = self
        self.context.add_llm_tools(doubao_tool)

        qwen_tool = QwenEditTool()
        qwen_tool.plugin_instance = self
        self.context.add_llm_tools(qwen_tool)

        logger.info(f"🎨 AI图片工具插件已加载 v1.0.0")
