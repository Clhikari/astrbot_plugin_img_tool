from astrbot.api.all import *
from astrbot.api import logger
import astrbot.api.message_components as Comp
import aiohttp
import json
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

    # 需要保存插件实例引用
    plugin_instance: object = None

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) :
        """执行图片生成"""
        prompt = kwargs.get("prompt", "")

        if not prompt:
            yield logger.warning("缺少图片描述")

        # 获取事件对象
        event = context.context.event
        event: AstrMessageEvent
        # 发送生成中提示
        event.plain_result("🛠️正在调用工具DoubaoDrawTool")

        # API 请求
        url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.plugin_instance.api_key}",
        }
        data = {
            "model": self.plugin_instance.endpoint_id,
            "prompt": prompt,
        }

        image_url = ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"API 请求失败，状态码: {resp.status}, 错误: {error_text}")
                        yield logger.error(f"API请求失败: {error_text}")
                        return
                    result = await resp.json()

                    if "data" in result and len(result["data"]) > 0:
                        image_url = result["data"][0].get("url")
                    else:
                        logger.error(f"API返回结构异常: {result}")

        except Exception as e:
            logger.error(f"生成过程中发生异常：{str(e)}")
            yield f"生成失败: {str(e)}"

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
            yield logger.error("生成失败，未获取到图片 URL")

    async def _get_user_image_url(self, event: AstrMessageEvent) -> str | None:
        """从 AstrBot 事件中提取图片 URL"""
        try:
            # 检查当前消息中是否有图片
            for component in event.message_obj.message:
                if isinstance(component, Comp.Image):
                    return component.url
            return ""
        except Exception as e:
            logger.error(f"提取图片失败: {e}")
            return ""


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
        logger.info(f"prompt：{instruction}")
        event = context.context.event
        event: AstrMessageEvent

        # 找图
        base64_image = await self._get_user_image_url(event)
        if not base64_image:
            yield event.plain_result("❌ 请先发送一张图片，再说出修图指令哦。")
            return

        # 调用阿里云 - 同步模式
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.plugin_instance.aliyun_api_key}",
        }
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
            "parameters": {
                "n": 1,
                "negative_prompt": "低质量，低分辨率，残缺、多余的手指、比例不良",
                "prompt_extend": True,
                "watermark": False,
                "size": "2048*2048",
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"❌ 阿里云API报错: {err}")
                        return

                    result = await resp.json()

                    if "output" in result and "choices" in result["output"]:
                        content = result["output"]["choices"][0]["message"]["content"]
                        # 找到image字段
                        final_img = next(
                            (item["image"] for item in content if "image" in item),
                            None,
                        )

                        if final_img:
                            yield event.chain_result([
                                Comp.At(qq=event.get_sender_id()),
                                Comp.Image.fromURL(final_img),
                            ])
                        else:
                            yield event.plain_result("❌ 未能获取到修改后的图片")
                    else:
                        logger.error(f"❌ API返回异常: {result}")

        except Exception as e:
            logger.error(f"❌ 异常: {e}")

    async def _get_user_image_url(self, event) -> str | None:
        """获取图片并转换为Base64"""
        for component in event.message_obj.message:
            if isinstance(component, Comp.Image):
                url = component.url
                logger.info(f"原始图片URL: {url}")

                try:
                    # 下载图片
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                logger.error(f"图片下载失败: {resp.status}")
                                return None

                            image_data = await resp.read()

                            # 转Base64
                            encoded = base64.b64encode(image_data).decode("utf-8")

                            # 通过文件头魔数判断真实格式
                            if image_data[:4] == b'\x89PNG':
                                content_type = "image/png"
                            elif image_data[:2] in (b'\xff\xd8', b'\xff\xdb'):
                                content_type = "image/jpeg"
                            elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
                                content_type = "image/webp"
                            else:
                                # 尝试从响应头获取
                                content_type = resp.headers.get("Content-Type", "image/jpeg")

                            # 返回标准格式
                            base64_image = f"data:{content_type};base64,{encoded}"
                            logger.info(
                                f"✅ 图片已转换为Base64 (前50字符): {base64_image[:50]}..."
                            )
                            return base64_image

                except Exception as e:
                    logger.error(f"图片处理失败: {e}")
                    return None
        return None


class DoubaoImagePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

        # 获取【绝对路径】，确保在 Linux/Docker 下路径正确
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, "config.json")

        logger.info(f"📂 插件所在目录: {self.base_dir}")
        logger.info(f"🔍 正在寻找配置文件: {self.config_path}")

        # 检查目录下到底有哪些文件
        try:
            files_in_dir = os.listdir(self.base_dir)
            logger.info(f"📄 目录下的文件列表: {files_in_dir}")

            if "config.json" not in files_in_dir:
                logger.error(
                    f"❌ 致命错误: 在 {self.base_dir} 下没有找到 config.json！"
                )
                logger.error("请检查文件名是否正确？(比如是不是叫 config.json.txt ?)")
        except Exception as e:
            logger.error(f"无法读取目录列表: {e}")

        self.volc_api_key = ""
        self.volc_endpoint_id = ""
        self.aliyun_api_key = ""

        # 读取配置文件
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.volc_api_key = config.get("volc_api_key", "")
                    self.volc_endpoint_id = config.get("volc_endpoint_id", "")
                    self.aliyun_api_key = config.get("aliyun_api_key", "")

                    logger.info("✅ 成功读取 config.json")
            except Exception as e:
                logger.error(f"❌ 读取 config.json 失败 (格式错误?): {e}")
        else:
            logger.warning(f"❌ 配置文件不存在: {self.config_path}")

        # 注册工具
        doubao_tool = DoubaoDrawTool()
        doubao_tool.plugin_instance = self
        self.context.add_llm_tools(doubao_tool)

        qwen_tool = QwenEditTool()
        qwen_tool.plugin_instance = self
        self.context.add_llm_tools(qwen_tool)

        logger.info(
            f"插件加载完毕。阿里云Key状态: {'✅' if self.aliyun_api_key else '❌'}"
        )
