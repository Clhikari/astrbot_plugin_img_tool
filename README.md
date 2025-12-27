# AstrBot AI Image Tool Plugin

<p align="center">
  <img src="https://count.getloli.com/@Clhikari?name=Clhikari&theme=booru-lisu&padding=7&offset=0&align=center&scale=0.8&pixelated=1&darkmode=auto" alt="Moe Counter">
</p>

集成了**火山引擎（豆包）的文生图能力**和**阿里云（通义千问）的图片编辑能力**。

## ✨ 支持模型

本插件经过测试，主要支持以下模型服务：

| 功能 | 服务商 | 模型/系列 | 说明 |
| :--- | :--- | :--- | :--- |
| **文生图** | 火山引擎 (Volcengine) | **Doubao-Seedream 系列** | 需在火山方舟控制台创建推理接入点 |
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

---

## ⚙️ 配置说明

### 配置参数一览

| 参数名 | 说明 | 默认值/备注 |
| :--- | :--- | :--- |
| `volc_api_key` | 火山引擎 API Key | **必填**（用于文生图） |
| `volc_endpoint_id` | 火山引擎推理接入点 ID | **必填**（格式：`ep-xxxxxxxxxx-xxxxx`） |
| `aliyun_api_key` | 阿里云 DashScope API Key | **必填**（用于修图） |
| `edit_image_size` | 修图输出分辨率 | `1536*1536` |
| `enable_negative_prompt` | 启用负面提示词 | `true` |
| `negative_prompt` | 负面提示词内容 | 低质量，低分辨率... |

---

## 📖 详细配置教程

### 一、获取火山引擎（豆包）配置

#### 步骤 1：注册并登录火山引擎

1. 访问 [火山引擎官网](https://www.volcengine.com/)
2. 注册账号并完成实名认证

#### 步骤 2：进入火山方舟控制台

1. 访问 [火山方舟控制台](https://console.volcengine.com/ark)
2. 首次使用需开通服务

#### 步骤 3：获取 API Key

1. 在左侧菜单找到 **「API Key 管理」**（位于「系统管理」下方）
2. 点击 **「创建 API Key」**
3. 复制生成的 API Key，填入插件配置的 `volc_api_key`

> ⚠️ API Key 只显示一次，请妥善保存！

#### 步骤 4：创建推理接入点获取 Endpoint ID

1. 在左侧菜单选择 **「模型推理」** → **「在线推理」**

2. 点击页面上的 **「+ 创建推理接入点」** 按钮

3. 填写接入点信息：

   | 配置项 | 填写内容 |
   |-------|---------|
   | **接入点名称** | 自定义名称，可以随便取个
   | **接入点描述** | 可不填 |
   | **推理模式** | 选择 **「指定单一模型」** |
   | **接入模型** | 选择 **「火山方舟平台」**，点击 **「+ 添加模型」**，搜索并选择 **Doubao-Seedream** 系列（如 `Doubao-Seedream-4.0` 或 `Doubao-Seedream-4.5`） |
   | **接入模式** | 选择 **「按Token付费」**（基础模式，按实际使用量付费） |

4. 点击右下角 **「创建并接入」**

5. 创建成功后，返回「在线推理」列表页面

6. 在列表中找到刚创建的接入点，复制 **「接入点名称/ID」** 列中的 ID（格式如 `ep-20251217145237-w5snk`）

7. 将复制的 ID 填入插件配置的 `volc_endpoint_id`

> 💡 **提示**：接入点 ID 以 `ep-` 开头，后面跟着一串数字和字母。

---

### 二、获取阿里云（DashScope）配置

#### 步骤 1：注册并登录阿里云

1. 访问 [阿里云官网](https://www.aliyun.com/)
2. 注册账号并完成实名认证

#### 步骤 2：开通 DashScope 服务

1. 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 首次使用需开通服务（通义千问系列一般有免费额度）

#### 步骤 3：获取 API Key

1. 进入 [API-KEY 管理页面](https://dashscope.console.aliyun.com/apiKey)
2. 点击 **「创建新的 API-KEY」**
3. 复制生成的 API Key，填入插件配置的 `aliyun_api_key`

> ⚠️ API Key 只显示一次，请妥善保存！

#### 步骤 4：确认模型权限

确保你的账号已开通 **Qwen-Image-Edit** 系列模型的使用权限：
- 在控制台 → 模型广场 → 搜索 "qwen-image-edit"
- 确认模型状态为「已开通」

---

## 🔧 配置示例

在 AstrBot 管理面板中填入配置：

```yaml
# 火山引擎配置（文生图）
volc_api_key: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
volc_endpoint_id: "ep-20251217145237-w5snk"

# 阿里云配置（修图）
aliyun_api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx"

# 可选配置
edit_image_size: "1536*1536"
enable_negative_prompt: true
negative_prompt: "低质量，低分辨率，模糊，畸变"
```

---

## ⚠️ 注意事项

1. **模型能力要求**：所使用的大语言模型需要有调用函数（Function Calling / Tools）的能力
2. **费用说明**：
   - 火山引擎和阿里云均有免费额度，超出后按调用次数计费
   - 建议在控制台设置用量告警
3. **网络要求**：服务器需能正常访问火山引擎和阿里云 API

---

## 🔍 常见问题

<details>
<summary><b>Q: 提示「API请求失败」怎么办？</b></summary>

1. 检查 API Key 是否正确复制（无多余空格）
2. 确认账号是否完成实名认证
3. 查看控制台是否有欠费或额度用尽
4. 检查 Endpoint ID 格式是否正确（以 `ep-` 开头）

</details>

<details>
<summary><b>Q: 在「添加模型」时找不到 Doubao-Seedream？</b></summary>

1. 确认「接入模型」处已选择「火山方舟平台」
2. 在弹出的模型选择框中搜索 "Seedream"
3. 如果仍找不到，可能需要先在「模型广场」中开通该模型

</details>

<details>
<summary><b>Q: 修图功能没有反应？</b></summary>

1. 确认图片格式支持（JPG/PNG/WebP）
2. 检查图片大小是否超过限制（默认 10MB）
3. 确保先发送/引用图片，再发送修改指令

</details>

<details>
<summary><b>Q: 接入点状态显示「异常」？</b></summary>

1. 检查账户余额是否充足
2. 确认所选模型是否可用
3. 尝试删除后重新创建接入点

</details>

---

## 📦 依赖项

- aiohttp
- pydantic

---

## 📄 许可证 (License)

本项目遵循 [MIT License](LICENSE) 开源协议。
