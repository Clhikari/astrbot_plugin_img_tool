import asyncio
import base64
import mimetypes
import re
from pathlib import Path
from typing import Any

import aiohttp

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.all import AstrMessageEvent
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.message.message_event_result import MessageChain


@register(
    "AIImagePlugin",
    "Clhikari",
    "AI图片生成与编辑工具",
    "1.1.0",
    "https://github.com/Clhikari/astrbot_plugin_img_tool",
)
class AIImagePlugin(Star):
    HTTP_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
    IMAGE_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
    LOCAL_IMAGE_PATH_PATTERN = re.compile(
        r"(?P<path>(?:/[^\s\"'`]+|[A-Za-z]:\\[^\r\n\t\"'`]+)\.(?:png|jpe?g|webp))",
        re.IGNORECASE,
    )
    IMAGE_SIZE_PATTERN = re.compile(r"^(\d{3,4})[xX*](\d{3,4})$")

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._session: aiohttp.ClientSession | None = None

        if not self.config.get("volc_api_key"):
            logger.warning(
                "[AIImagePlugin] volc_api_key is not configured, draw_image_doubao will be unavailable."
            )

        if not self.config.get("aliyun_api_key"):
            logger.warning(
                "[AIImagePlugin] aliyun_api_key is not configured, edit_image_qwen will be unavailable."
            )

    def _get_float_conf(
        self,
        key: str,
        default: float,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float:
        value = self.config.get(key, default)
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default

        if min_value is not None:
            number = max(min_value, number)
        if max_value is not None:
            number = min(max_value, number)
        return number

    def _get_int_conf(
        self,
        key: str,
        default: int,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        value = self.config.get(key, default)
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default

        if min_value is not None:
            number = max(min_value, number)
        if max_value is not None:
            number = min(max_value, number)
        return number

    def _get_bool_conf(self, key: str, default: bool) -> bool:
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return bool(value)

    @classmethod
    def _normalize_image_size(cls, value: str, default: str) -> str:
        if not value:
            return default

        matched = cls.IMAGE_SIZE_PATTERN.match(value.strip())
        if not matched:
            return default

        width = int(matched.group(1))
        height = int(matched.group(2))
        if width < 512 or width > 2048 or height < 512 or height > 2048:
            return default

        return f"{width}*{height}"

    @staticmethod
    def _detect_image_type_from_header(
        header: bytes, content_type_header: str | None = None
    ) -> str:
        if header[:4] == b"\x89PNG":
            return "image/png"
        if header[:2] in (b"\xff\xd8", b"\xff\xdb"):
            return "image/jpeg"
        if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WEBP":
            return "image/webp"

        if content_type_header and "/" in content_type_header:
            return content_type_header.split(";", 1)[0].strip()
        return "image/jpeg"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": "astrbot_plugin_img_tool/1.1.0"}
            )
        return self._session

    async def _request_json_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_payload: dict[str, Any] | None = None,
        action_name: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        timeout_sec = self._get_float_conf("request_timeout_sec", 60, 5, 180)
        retry_count = self._get_int_conf("request_retry_count", 2, 0, 5)
        max_attempts = retry_count + 1

        for attempt in range(1, max_attempts + 1):
            try:
                session = await self._get_session()
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_payload,
                    timeout=aiohttp.ClientTimeout(total=timeout_sec),
                ) as resp:
                    if (
                        resp.status in self.HTTP_RETRYABLE_STATUS
                        and attempt < max_attempts
                    ):
                        logger.warning(
                            "[%s] attempt %s/%s got retryable status %s",
                            action_name,
                            attempt,
                            max_attempts,
                            resp.status,
                        )
                        await asyncio.sleep(min(0.8 * attempt, 2.5))
                        continue

                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error(
                            "[%s] HTTP %s: %s",
                            action_name,
                            resp.status,
                            err_text[:300],
                            exc_info=True,
                        )
                        return None, f"HTTP {resp.status}: {err_text[:120]}"

                    return await resp.json(), None

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < max_attempts:
                    logger.warning(
                        "[%s] attempt %s/%s failed, retrying: %s",
                        action_name,
                        attempt,
                        max_attempts,
                        e,
                    )
                    await asyncio.sleep(min(0.8 * attempt, 2.5))
                    continue
                logger.error("[%s] request failed: %s", action_name, e, exc_info=True)
                return None, str(e)
            except Exception as e:
                logger.error("[%s] unexpected error: %s", action_name, e, exc_info=True)
                return None, str(e)

        return None, "request failed after retries"

    async def _get_user_image_base64(self, url: str | None) -> str | None:
        if not url or not url.startswith(("http://", "https://")):
            return None

        logger.info("Downloading user image: %s", url)

        max_mb = self._get_float_conf("max_image_size_mb", 10, 1, 30)
        max_bytes = int(max_mb * 1024 * 1024)
        timeout_sec = self._get_float_conf("request_timeout_sec", 60, 5, 180)

        try:
            session = await self._get_session()
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout_sec),
            ) as resp:
                if resp.status != 200:
                    logger.error(
                        "Image download failed, HTTP %s", resp.status, exc_info=True
                    )
                    return None

                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    logger.warning(
                        "Image too large by Content-Length: %s > %s bytes",
                        content_length,
                        max_bytes,
                    )
                    return None

                header = await resp.content.read(16)
                if not header:
                    logger.warning("Downloaded empty image body")
                    return None

                content_type = self._detect_image_type_from_header(
                    header,
                    resp.headers.get("Content-Type"),
                )

                chunks = [header]
                total_size = len(header)

                async for chunk in resp.content.iter_chunked(8192):
                    chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        logger.warning(
                            "Image exceeded configured size limit: %s > %s bytes",
                            total_size,
                            max_bytes,
                        )
                        return None

                image_data = b"".join(chunks)
                encoded = base64.b64encode(image_data).decode("utf-8")
                logger.info(
                    "Image converted to base64 (%s, %s bytes)", content_type, total_size
                )
                return f"data:{content_type};base64,{encoded}"

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error("Image download failed: %s", e, exc_info=True)
            return None
        except Exception as e:
            logger.error("Image processing failed: %s", e, exc_info=True)
            return None

    @classmethod
    def _resolve_local_image_path(cls, path_text: str | None) -> Path | None:
        if not path_text:
            return None

        raw_path = path_text.strip().strip("\"'`")
        if not raw_path:
            return None

        candidate = Path(raw_path)
        if not candidate.is_absolute():
            return None

        try:
            resolved = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError):
            return None

        if not resolved.is_file():
            return None

        if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return None

        return resolved

    async def _get_local_image_base64(self, path_text: str | None) -> str | None:
        image_path = self._resolve_local_image_path(path_text)
        if not image_path:
            return None

        logger.info("Loading local image: %s", image_path)

        max_mb = self._get_float_conf("max_image_size_mb", 10, 1, 30)
        max_bytes = int(max_mb * 1024 * 1024)

        try:
            file_size = image_path.stat().st_size
            if file_size > max_bytes:
                logger.warning(
                    "Local image exceeded configured size limit: %s > %s bytes",
                    file_size,
                    max_bytes,
                )
                return None

            image_data = await asyncio.to_thread(image_path.read_bytes)
            if not image_data:
                logger.warning("Local image is empty: %s", image_path)
                return None

            content_type = self._detect_image_type_from_header(
                image_data[:16],
                mimetypes.guess_type(str(image_path))[0],
            )
            encoded = base64.b64encode(image_data).decode("utf-8")
            logger.info(
                "Local image converted to base64 (%s, %s bytes)",
                content_type,
                len(image_data),
            )
            return f"data:{content_type};base64,{encoded}"
        except Exception as e:
            logger.error("Local image processing failed: %s", e, exc_info=True)
            return None

    async def _get_target_image(self, event: AstrMessageEvent) -> str | None:
        current_chain = event.message_obj.message
        for comp in current_chain:
            if isinstance(comp, Comp.Image):
                return await self._get_user_image_base64(comp.url)

        reply_comp: Comp.Reply | None = None
        for comp in current_chain:
            if isinstance(comp, Comp.Reply):
                reply_comp = comp

        if not reply_comp or not reply_comp.chain:
            return None

        for inner_comp in reply_comp.chain:
            if isinstance(inner_comp, Comp.Image):
                return await self._get_user_image_base64(inner_comp.url)
        return None

    @classmethod
    def _extract_first_image_url(cls, text: str) -> str | None:
        matched = cls.IMAGE_URL_PATTERN.search(text)
        if not matched:
            return None
        candidate = matched.group(0).rstrip(".,;!?)\"]'")
        return candidate

    @classmethod
    def _extract_first_local_image_path(cls, text: str) -> str | None:
        matched = cls.LOCAL_IMAGE_PATH_PATTERN.search(text)
        if not matched:
            return None
        return matched.group("path").rstrip(".,;!?)\"]'")

    @filter.llm_tool(name="draw_image_doubao")
    async def draw_image(self, event: AstrMessageEvent, prompt: str):
        """Generate a new image with Doubao from text prompt.

        Args:
            prompt(string): Text prompt for image generation.
        """
        prompt = (prompt or "").strip()
        if not prompt:
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
            return "用户未设置 volc_api_key 或 volc_endpoint_id"

        payload: dict[str, Any] = {
            "model": endpoint_id,
            "prompt": prompt,
            "watermark": self._get_bool_conf("draw_add_watermark", False),
        }

        raw_size = str(self.config.get("draw_image_size", "")).strip()
        if raw_size.lower() in {"1k", "2k", "4k"}:
            payload["size"] = raw_size.lower()
        else:
            draw_size = self._normalize_image_size(raw_size, "")
            if draw_size:
                payload["size"] = draw_size.replace("*", "x")

        result, error = await self._request_json_with_retry(
            "POST",
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json_payload=payload,
            action_name="draw_image_doubao",
        )
        if error or not result:
            await event.send(MessageChain().message("❌ 文生图请求失败，请查看日志"))
            return f"文生图请求失败: {error or 'unknown error'}"

        data = result.get("data") if isinstance(result, dict) else None
        if isinstance(data, list) and data:
            image_url = data[0].get("url")
            if image_url:
                await event.send(
                    MessageChain()
                    .message("✨ 文生图完成：\n")
                    .at(event.get_sender_name(), event.get_sender_id())
                    .url_image(image_url)
                )
                return f"文生图成功，提示词: {prompt}"

        logger.error("draw_image_doubao returned unexpected payload: %s", result)
        await event.send(MessageChain().message("❌ 未获取到生成图片，请查看日志"))
        return f"文生图返回异常: {result}"

    @filter.llm_tool(name="edit_image_qwen")
    async def edit_image(self, event: AstrMessageEvent, instruction: str):
        """Edit an existing image with Qwen-Image-Edit.

        Args:
            instruction(string): Edit instruction text. You can include an image URL.
        """
        instruction = (instruction or "").strip()
        if not instruction:
            await event.send(MessageChain().message("❌ 请提供修图指令"))
            return "用户未提供修图指令"

        base64_img = await self._get_target_image(event)

        if not base64_img:
            image_url = self._extract_first_image_url(instruction)
            if image_url:
                base64_img = await self._get_user_image_base64(image_url)
                instruction = (
                    instruction.replace(image_url, "").strip() or "按原意优化图像"
                )

        if not base64_img:
            local_image_path = self._extract_first_local_image_path(instruction)
            if local_image_path:
                base64_img = await self._get_local_image_base64(local_image_path)
                instruction = (
                    instruction.replace(local_image_path, "").strip() or "按原意优化图像"
                )

        if not base64_img:
            await event.send(
                MessageChain().message(
                    "❌ 请先发送一张图片（或回复图片 / 在指令里附图片URL）再执行修图。"
                )
            )
            return "未找到可用图片输入"

        await event.send(MessageChain().message("🎨 正在修图中，请稍候..."))

        api_key = self.config.get("aliyun_api_key")
        if not api_key:
            await event.send(
                MessageChain().message("❌ 配置缺失：请设置 aliyun_api_key")
            )
            return "用户未配置 aliyun_api_key"

        size = self._normalize_image_size(
            str(self.config.get("edit_image_size", "1536*1536")),
            "1536*1536",
        )
        enable_neg = self._get_bool_conf("enable_negative_prompt", True)
        neg_prompt = str(
            self.config.get("negative_prompt", "低质量，低分辨率，模糊，畸变")
        ).strip()
        qwen_model = str(
            self.config.get("qwen_model_name", "qwen-image-edit-plus-2025-10-30")
        ).strip()

        params: dict[str, Any] = {
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
                        ],
                    }
                ]
            },
            "parameters": params,
        }

        result, error = await self._request_json_with_retry(
            "POST",
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json_payload=payload,
            action_name="edit_image_qwen",
        )
        if error or not result:
            await event.send(MessageChain().message("❌ 修图请求失败，请查看日志"))
            return f"修图请求失败: {error or 'unknown error'}"

        final_img = None
        output = result.get("output") if isinstance(result, dict) else None
        choices = output.get("choices") if isinstance(output, dict) else None
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("image"):
                        final_img = item["image"]
                        break

        if final_img:
            await event.send(
                MessageChain()
                .message("✨ 修图完成：\n")
                .at(event.get_sender_name(), event.get_sender_id())
                .url_image(final_img)
            )
            return f"修图成功，指令: {instruction}"

        logger.error("edit_image_qwen returned unexpected payload: %s", result)
        await event.send(MessageChain().message("❌ 未能获取到修图结果，请查看日志"))
        return f"修图返回异常: {result}"

    async def terminate(self):
        """Release HTTP session on plugin unload."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("AIImagePlugin session closed.")
