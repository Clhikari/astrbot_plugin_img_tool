from astrbot.api.all import AstrMessageEvent
from astrbot.api.star import register, Star, Context
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import filter
from astrbot.core.message.message_event_result import MessageChain
import astrbot.api.message_components as Comp
import aiohttp
import base64

@register(
    "AIImagePlugin",
    "Clhikari",
    "AI图片生成与编辑工具",
    "1.0.1",
    "https://github.com/Clhikari/astrbot_plugin_img_tool",
)
class AIImagePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._session = None
        # 检查配置
        if not self.config.get("volc_api_key"):
            logger.warning(
                "⚠️ [AIImagePlugin]未配置 volc_api_key，文生图功能将无法使用。"
            )

    async def _get_user_image_base64(self, url: str | None):
        """获取图片并流式转换为Base64"""
        logger.info(f"正在下载图片: {url}")
        # 获取用户配置的最大限制，默认为 10MB
        try:
            max_mb = float(self.config.get("max_image_size_mb", 10))
        except (ValueError, TypeError):
            max_mb = 10
        max_bytes = int(max_mb * 1024 * 1024)

        try:
            session = await self._get_session()
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30),  # pyright: ignore[reportArgumentType]
            ) as resp:
                if resp.status != 200:
                    logger.error(f"图片下载失败 [{resp.status}]", exc_info=True)
                    return None

                # 先读取文件头用于类型判断（只读前16字节）
                header = await resp.content.read(16)
                content_type = self._detect_image_type_from_header(header, resp)

                # 检查Content-Length，对大文件提前拒绝
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes * 1024 * 1024:
                    logger.warning(
                        f"图片过大: {content_length} bytes, 超过限制 {max_mb}MB"
                    )
                    return None

                # 分块读取并累积
                chunks = [header]  # 包含文件头
                total_size = len(header)

                async for chunk in resp.content.iter_chunked(8192):  # 8KB块
                    chunks.append(chunk)
                    total_size += len(chunk)

                    # 边下载边检查大小
                    if total_size > max_bytes * 1024 * 1024:
                        logger.warning(f"图片超过{max_bytes}限制")
                        return None

                # 合并并编码
                image_data = b"".join(chunks)
                encoded = base64.b64encode(image_data).decode("utf-8")

                base64_image = f"data:{content_type};base64,{encoded}"
                logger.info(f"✅ 图片转换完成 ({content_type}, {total_size} bytes)")
                return base64_image

        except aiohttp.ClientError as e:
            logger.error(f"下载失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return None

    @staticmethod
    def _detect_image_type_from_header(
        header: bytes, resp: aiohttp.ClientResponse
    ) -> str:
        """从文件头判断图片类型"""
        if header[:4] == b"\x89PNG":
            return "image/png"
        elif header[:2] in (b"\xff\xd8", b"\xff\xdb"):
            return "image/jpeg"
        elif header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
            return "image/webp"

        # 从响应头获取
        return resp.headers.get("Content-Type", "image/jpeg")

    async def _get_target_image(self, event: AstrMessageEvent) -> str | None:
        """获取目标图片：优先当前消息的图，其次是回复消息的图"""
        # 检查当前消息
        current_chain = event.message_obj.message
        for comp in current_chain:
            if isinstance(comp, Comp.Image):
                return await self._get_user_image_base64(comp.url)

        # 检查引用的消息
        reply_comp: Comp.Reply | None = None
        for comp in current_chain:
            if isinstance(comp, Comp.Reply):
                reply_comp = comp
        if not reply_comp:
            return None
        # 在chain属性查找图片
        if reply_comp.chain:
            for inner_comp in reply_comp.chain:
                if isinstance(inner_comp, Comp.Image):
                    return await self._get_user_image_base64(inner_comp.url)
        return None

    @filter.llm_tool(name="draw_image_doubao")
    async def draw_image(self, event: AstrMessageEvent, prompt: str):
        """
        【文生图】使用豆包模型从零绘制/生成一张新图片。

        Args:
            prompt (str): 画面描述
        """
        if not prompt:
            logger.warning("❌ 缺少图片描述")
            await event.send(MessageChain().message("❌ 请提供图片描述"))
            return "用户未提供图片描述"

        await event.send(MessageChain().message("🎨 正在绘制中..."))

        api_key = self.config.get("volc_api_key")
        endpoint_id = self.config.get("volc_endpoint_id")

        if not api_key or not endpoint_id:
            await event.send(
                MessageChain().message(
                    "❌ 插件配置缺失：请设置 volc_api_key 和 volc_endpoint_id"
                )
            )
            return "用户未设置 volc_api_key 和 volc_endpoint_id"

        url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": endpoint_id,
            "prompt": prompt,
        }

        try:
            session = await self._get_session()
            async with session.post(
                url, headers=headers, json=payload, timeout=30
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    logger.error(
                        f"❌ API请求失败 ({resp.status}): {err_text[:100]}",
                        exc_info=True,
                    )
                    await event.send(MessageChain().message("❌ API请求失败,详细看日志"))
                    return f"❌ API请求失败 ({resp.status}): {err_text[:100]}"

                result = await resp.json()

                if "data" in result and result["data"]:
                    image_url = result["data"][0].get("url")
                    await event.send(
                        MessageChain()
                        .message("✨ 修图完成：\n")
                        .at(event.get_sender_name(), event.get_sender_id())
                        .url_image(image_url)
                    )
                    return f"成功生成了图片，提示词为：{prompt}，图片已发送给用户。"
                else:
                    logger.error(f"❌ API返回数据异常: {result}", exc_info=True)
                    await event.send(MessageChain().message("❌ API返回数据异常,详细看日志"))
                    return f"❌ API返回数据异常: {result}"
        except Exception as e:
            logger.error(f"文生图异常: {e}", exc_info=True)
            await event.send(MessageChain().message(f"❌ 生成出错: {str(e)}"))
            return f"❌ 图片生成出错: {str(e)},终止调用"
        
    @filter.llm_tool(name="edit_image_qwen")
    async def edit_image(self, event: AstrMessageEvent, instruction: str):
        """
        【修图/改图】使用Qwen模型修改用户发送的图片。

        Args:
            instruction (str): 修改指令，例如'把红色改成蓝色'
        """
        base64_img = await self._get_target_image(event)
        if not base64_img:
            await event.send(
                MessageChain().message(
                    "❌ 请先发送一张图片（或回复一张图片），再说出修图指令。"
                )
            )
            return "用户未发送图片"

        await event.send(MessageChain().message("🎨 正在修图中，请稍候..."))

        api_key = self.config.get("aliyun_api_key")
        if not api_key:
            await event.send(
                MessageChain().message("❌ 配置缺失：请设置 aliyun_api_key")
            )
            return "用户未配置aliyun_api_key"

        # 读取配置
        size = self.config.get("edit_image_size", "1536*1536")
        enable_neg = self.config.get("enable_negative_prompt", True)
        neg_prompt = self.config.get("negative_prompt", "低质量，低分辨率，模糊，畸变")
        qwen_model = self.config.get(
            "qwen_model_name", "qwen-image-edit-plus-2025-10-30"
        )

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        params = {
            "n": 1,
            "prompt_extend": True,
            "watermark": False,
            "size": size,
        }
        if enable_neg and neg_prompt:
            params["negative_prompt"] = neg_prompt

        payload = {
            "model": qwen_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": base64_img},
                            {"text": instruction},
                        ]
                    }
                ]
            },
            "parameters": params,
        }

        try:
            session = await self._get_session()
            async with session.post(
                url, headers=headers, json=payload, timeout=60
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(
                        f"❌ 阿里云API报错 ({resp.status}): {err[:100]}", exc_info=True
                    )
                    await event.send(MessageChain().message("❌ 阿里云API报错,详细看日志"))
                    return "❌ 阿里云API报错,终止调用"
                result = await resp.json()

                if "output" in result and "choices" in result["output"]:
                    content = result["output"]["choices"][0]["message"]["content"]
                    # 健壮性获取
                    final_img = None
                    for item in content:
                        if "image" in item:
                            final_img = item["image"]
                            break

                    if final_img:
                        await event.send(
                            MessageChain()
                            .message("✨ 修图完成：\n")
                            .at(event.get_sender_name(), event.get_sender_id())
                            .url_image(final_img)
                        )
                        return f"成功生成了图片,prompt为:{instruction}，图片已发送给用户。"
                await event.send(
                    MessageChain().message("❌ 未能获取到修改后的图片，请检查日志。")
                )

        except Exception as e:
            logger.error(f"修图异常: {e}", exc_info=True)
            await event.send(MessageChain().message("❌ 修图过程发生异常详请看日志"))
            return f"工具执行发生严重系统错误: {e}"
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取复用的Session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def terminate(self):
        """插件卸载时释放资源"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("AIImagePlugin Session closed.")
