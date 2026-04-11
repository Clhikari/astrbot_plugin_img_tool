# AstrBot AI Image Tool Plugin

<p align="center">
  <img src="https://count.getloli.com/@Clhikari?name=Clhikari&theme=booru-lisu&padding=7&offset=0&align=center&scale=0.8&pixelated=1&darkmode=auto" alt="Moe Counter">
</p>

集成火山引擎豆包文生图和阿里云通义千问修图能力，适合在 AstrBot 里直接生成图片或修改已有图片。

## ✨ 支持模型

| 功能 | 服务商 | 模型/系列 | 说明 |
| :--- | :--- | :--- | :--- |
| 文生图 | 火山引擎 (Volcengine) | Doubao-Seedream 系列 | 需要在火山方舟控制台创建推理接入点 |
| 修图/改图 | 阿里云 (DashScope) | Qwen-Image-Edit 系列 | 默认模型为 `qwen-image-edit-plus-2025-10-30`，也可自行配置 |

## 🚀 功能特性

### 1. 文生图

使用豆包 Seedream 模型，根据文本描述直接生成图片。

- 支持自定义 Prompt
- 支持配置输出尺寸
- 支持配置是否添加水印

### 2. 图片编辑

使用通义千问图像编辑模型，对现有图片进行指令式修改。

- 支持当前消息中的图片
- 支持回复链中的图片
- 支持从指令文本中的图片 URL 取图
- 兼容框架传入的本地临时图片路径

---

## ⚙️ 配置说明

### 配置参数一览

| 参数名 | 说明 | 默认值/备注 |
| :--- | :--- | :--- |
| `volc_api_key` | 火山引擎 API Key | 必填，用于文生图 |
| `volc_endpoint_id` | 火山引擎推理接入点 ID | 必填，通常以 `ep-` 开头 |
| `draw_image_size` | 文生图输出分辨率 | 可留空，也支持 `1k`、`2k`、`4k`、`1024x1024` |
| `draw_add_watermark` | 文生图是否添加水印 | 默认 `false` |
| `aliyun_api_key` | 阿里云 DashScope API Key | 必填，用于修图 |
| `qwen_model_name` | 修图模型名称 | 默认 `qwen-image-edit-plus-2025-10-30` |
| `edit_image_size` | 修图输出分辨率 | 默认 `1536*1536` |
| `enable_negative_prompt` | 启用负面提示词 | 默认 `true` |
| `negative_prompt` | 负面提示词内容 | 默认 `低质量，模糊，畸变，错误人体结构` |
| `max_image_size_mb` | 输入图片大小上限 | 默认 `10` MB |
| `request_timeout_sec` | 下载图片和请求外部 API 的超时时间 | 默认 `60` 秒 |
| `request_retry_count` | 遇到 429、5xx 或网络超时时的重试次数 | 默认 `2` |

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

> ⚠️ API Key 只显示一次，请妥善保存。

#### 步骤 4：创建推理接入点获取 Endpoint ID

1. 在左侧菜单选择 **「模型推理」** → **「在线推理」**
2. 点击页面上的 **「+ 创建推理接入点」** 按钮
3. 填写接入点信息：

   | 配置项 | 填写内容 |
   | :--- | :--- |
   | **接入点名称** | 自定义名称，可以自行命名 |
   | **接入点描述** | 可不填 |
   | **推理模式** | 选择 **「指定单一模型」** |
   | **接入模型** | 选择 **「火山方舟平台」**，点击 **「+ 添加模型」**，搜索并选择 **Doubao-Seedream** 系列，如 `Doubao-Seedream-4.0` 或 `Doubao-Seedream-4.5` |
   | **接入模式** | 选择 **「按 Token 付费」** |

4. 点击右下角 **「创建并接入」**
5. 创建成功后，返回「在线推理」列表页面
6. 在列表中找到刚创建的接入点，复制 **「接入点名称/ID」** 列中的 ID，格式如 `ep-20251217145237-w5snk`
7. 将复制的 ID 填入插件配置的 `volc_endpoint_id`

> 💡 接入点 ID 以 `ep-` 开头，后面跟着一串数字和字母。

---

### 二、获取阿里云（DashScope）配置

#### 步骤 1：注册并登录阿里云

1. 访问 [阿里云官网](https://www.aliyun.com/)
2. 注册账号并完成实名认证

#### 步骤 2：开通 DashScope 服务

1. 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 首次使用需开通服务，通义千问系列一般有免费额度

#### 步骤 3：获取 API Key

1. 进入 [API-KEY 管理页面](https://dashscope.console.aliyun.com/apiKey)
2. 点击 **「创建新的 API-KEY」**
3. 复制生成的 API Key，填入插件配置的 `aliyun_api_key`

> ⚠️ API Key 只显示一次，请妥善保存。

#### 步骤 4：确认模型权限

确保你的账号已开通 **Qwen-Image-Edit** 系列模型的使用权限：

- 在控制台的模型广场中搜索 `qwen-image-edit`
- 确认模型状态为「已开通」

---

## 🔧 配置示例

在 AstrBot 管理面板中填入配置：

```yaml
# 火山引擎配置（文生图）
volc_api_key: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
volc_endpoint_id: "ep-20251217145237-w5snk"
draw_image_size: "1024x1024"
draw_add_watermark: false

# 阿里云配置（修图）
aliyun_api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
qwen_model_name: "qwen-image-edit-plus-2025-10-30"
edit_image_size: "1536*1536"
enable_negative_prompt: true
negative_prompt: "低质量，模糊，畸变，错误人体结构"

# 网络和输入限制
max_image_size_mb: 10
request_timeout_sec: 60
request_retry_count: 2
```

---

## 🧪 使用方式

### 文生图

- 直接发送“画一张……”“生成一张……”这类描述
- 插件会调用 `draw_image_doubao` 生成图片并返回结果

### 修图

- 发送图片后直接说修改要求
- 回复一张图片后说修改要求
- 在指令中直接附上图片 URL 再说修改要求

示例：

- `把这张图改成冬日街头风格`
- `给人物加一顶红色圣诞帽`
- `把这张图片改成赛博朋克风 https://example.com/demo.png`

---

## ⚠️ 注意事项

1. 所用大模型需要支持工具调用
2. 服务器需要能访问火山引擎和阿里云接口
3. 修图接口本身可能较慢，如果宿主工具超时较短，可以适当调高 `request_timeout_sec` 和 `request_retry_count`
4. 输入图片过大时，插件会在下载或读取阶段直接拒绝

---

## 🔍 常见问题

<details>
<summary><b>Q: 提示「API 请求失败」怎么办？</b></summary>

1. 检查 API Key 是否正确复制
2. 确认账号是否完成实名认证
3. 查看控制台是否有欠费或额度用尽
4. 检查服务器网络是否能访问对应服务

</details>

<details>
<summary><b>Q: 在「添加模型」时找不到 Doubao-Seedream？</b></summary>

1. 确认「接入模型」处已选择「火山方舟平台」
2. 在弹出的模型选择框中搜索 `Seedream`
3. 如果仍找不到，可能需要先在模型广场中开通该模型

</details>

<details>
<summary><b>Q: 修图时提示“未找到可用图片输入”怎么办？</b></summary>

确认满足下面任意一种方式：

1. 当前消息里直接带图片
2. 回复的是一条带图片的消息
3. 指令文本中带有可访问的图片 URL

</details>

<details>
<summary><b>Q: 为什么图片很小，修图还是可能超时？</b></summary>

图片上传只是前半段，真正耗时通常在服务端生成阶段。图片小，不代表修图接口一定很快。

</details>

---

## 📦 依赖项

- `aiohttp`
- `pydantic`

---

## 📄 许可证

本项目遵循 [MIT License](LICENSE) 开源协议。
