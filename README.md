# AstrBot AI Image Tool Plugin

<p align="center">
  <img src="https://count.getloli.com/@Clhikari?name=Clhikari&theme=booru-lisu&padding=7&offset=0&align=center&scale=0.8&pixelated=1&darkmode=auto" alt="Moe Counter">
</p>

集成了**火山引擎（豆包）的文生图能力和阿里云（通义千问）的图片**编辑能力。

## ✨ 支持模型

本插件经过测试，主要支持以下模型服务：

| 功能 | 服务商 | 模型/系列 | 说明 |
| :--- | :--- | :--- | :--- |
| **文生图** | 火山引擎 (Volcengine) | **Doubao-Seedream 系列** | 需在火山方舟控制台部署 Endpoint |
| **修图/改图** | 阿里云 (DashScope) | **Qwen-Image-Edit 系列** | 如 qwen-image-edit-plus 等 |

## 🚀 功能特性

### 1. 🎨 文生图 (DoubaoDrawTool)
使用豆包 Seedream 模型，根据文本描述从零生成图片。
- **触发方式**：用户发送 "画一张..."、"生成..." 等指令。
- **参数**：支持自定义 Prompt。

### 2. 🪄 图片编辑 (QwenEditTool)
使用通义千问图像编辑模型，对现有图片进行指令式修改。
- **触发方式**：发送图片后，回复或发送 "把红色改成蓝色"、"换成动漫风格" 等指令。
- **处理逻辑**：自动下载用户图片 -> 转 Base64 -> 调用阿里云 API -> 返回结果。

## ⚙️ 配置说明

请在 AstrBot 的配置文件或管理面板中填入以下参数：

| 参数名 | 说明 | 默认值/备注 |
| :--- | :--- | :--- |
| `volc_api_key` | 火山引擎 API Key | **必填** |
| `volc_endpoint_id` | 火山引擎推理接入点 ID | **必填** (ep-xxxxx) |
| `aliyun_api_key` | 阿里云 DashScope API Key | **必填** |
| `qwen_model_name` | 阿里云修图模型版本 | `qwen-image-edit-plus-2025-10-30` (可填任意可用型号) |
| `max_image_size_mb` | 图片上传最大限制 (MB) | `10` |

## ⚠️ 注意事项
- 所使用的大语言模型需要有调用函数（Function Calling / Tools）的能力。

## 📦 依赖项
- aiohttp
- pydantic

## 📄 许可证 (License)

本项目遵循 [MIT License](LICENSE) 开源协议。