这是一个为 [AstrBot](https://github.com/Soulter/AstrBot) 设计的图像处理函数工具。集成了**火山引擎（豆包）的文生图能力和阿里云（通义千问）的图片**编辑能力。

## ✨ 支持模型

本插件经过测试，主要支持以下模型服务：

| 功能 | 服务商 | 模型/系列 | 说明 |
| :--- | :--- | :--- | :--- |
| **文生图** | 火山引擎 (Volcengine) | **Doubao-Seedream 系列** | 需在火山方舟控制台部署 Endpoint |
| **修图/改图** | 阿里云 (DashScope) | **qwen-image-edit-plus-2025-10-30** | 针对特定日期版本的增强型修图模型 |

## 🚀 功能特性

### 1. 🎨 文生图 (DoubaoDrawTool)
使用豆包 Seedream 模型，根据文本描述从零生成图片。
- **触发方式**：用户发送 "画一张..."、"生成..." 等指令。
- **参数**：支持自定义 Prompt。

### 2. 🪄 图片编辑 (QwenEditTool)
使用通义千问图像编辑模型，对现有图片进行指令式修改。
- **触发方式**：发送图片后，回复或发送 "把红色改成蓝色"、"换成动漫风格" 等指令。
- **处理逻辑**：自动下载用户图片 -> 转 Base64 -> 调用阿里云 API -> 返回结果。

## ⚙️ 配置说明 (Configuration)

在使用前，请确保插件目录下存在 `config.json` 文件，并填入相应的参数。

### 1. 配置文件

在插件`config.json`：

```json
{
  "volc_api_key": "YOU_API_kEY",
  "volc_endpoint_id": "YOU_EP_ID",
  "aliyun_api_key": "YOU_API_KEY"
}
```
## 📦 依赖项
- aiohttp
- pydantic

## 📄 许可证 (License)

本项目遵循 [MIT License](LICENSE) 开源协议。
