# 小荷包报销助手

面向个人 / 小团队的报销助手：**发票识别 + 报销规则审核 + 智能问答**，提供 Web 界面与 REST API。

本项目基于开源项目 [megemini/AuditAgent](https://github.com/megemini/AuditAgent)（单据审核智能体，Apache-2.0）进行二次开发：保留了其「OCR + LLM 抽取发票字段」「结构化规则引擎」「基于规则的智能审核」核心思路，重构为 **FastAPI 后端 + 原生 Web 前端**，并针对报销场景裁剪与增强。

## 功能

| 模块 | 说明 | 是否依赖外部服务 |
|---|---|---|
| 发票识别 | 上传图片 / PDF，OCR 取字后由 LLM 抽取发票号码、金额、购销方等结构化字段 | 图片需 PaddleOCR；字段抽取需 LLM |
| 智能审核 | 依据规则引擎做确定性校验（发票要素、30 天时效、差旅住宿限额等） | 否，可离线 |
| 报销规则 | 规则的增删改查、搜索、导入 / 导出 / 重置 | 否 |
| 智能问答 | 基于当前规则库的流式问答 | 需 LLM |

> 关键设计：重依赖（PaddleOCR、PyMuPDF、OpenAI SDK）全部**懒加载**。未安装或未配置时，后端仍可启动，规则与审核功能不受影响。

## 目录结构

```
baoxiao.Assistant/
├── app/
│   ├── main.py              # FastAPI 入口（挂载路由与静态前端）
│   ├── config.py            # 配置（.env / 环境变量）
│   ├── core/                # 领域核心（改编自 AuditAgent）
│   │   ├── rules_engine.py      # 规则引擎
│   │   ├── invoice_recognizer.py# OCR/PDF + LLM 发票字段抽取
│   │   ├── ocr_manager.py       # PaddleOCR 懒加载封装
│   │   ├── llm_client.py        # OpenAI 兼容客户端（普通/流式）
│   │   └── city_tier.py         # 城市分级与住宿限额
│   ├── services/            # 业务服务层
│   └── routers/             # API 路由：health / invoices / rules / audit / chat
├── web/index.html           # 单文件 Web 前端（无需构建）
├── rules/default_rules.txt  # 默认报销规则（| 分隔）
├── data/                    # 上传文件与输出
├── tests/test_api.py        # API 冒烟测试
├── requirements.txt
└── run.py
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置（可选，用于发票字段抽取与智能问答）
copy .env.example .env      # Windows
# 编辑 .env，填写 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL

# 3. 启动
python run.py
```

打开 http://127.0.0.1:8000 使用 Web 界面；API 文档见 http://127.0.0.1:8000/docs 。

### 启用图片发票 OCR（可选）

```bash
pip install paddleocr paddlepaddle
```

不安装时，图片识别会返回明确提示；PDF（文字版）与规则、审核功能不受影响。

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查与配置状态 |
| GET | `/api/invoices/schema` | 发票字段结构 |
| POST | `/api/invoices/recognize` | 上传发票，返回 OCR 原文 + 结构化字段 |
| GET | `/api/rules` | 规则列表（`?category=` / `?search=`） |
| GET | `/api/rules/categories` | 规则统计 |
| POST | `/api/rules` | 新增规则 |
| PUT | `/api/rules/{rule_id}` | 更新规则 |
| DELETE | `/api/rules/{rule_id}` | 删除规则 |
| POST | `/api/rules/import` | 导入规则（txt，`?replace=`） |
| POST | `/api/rules/reset` | 重置为内置规则 |
| POST | `/api/audit` | 依据发票字段 + 上下文执行审核 |
| POST | `/api/chat` | 非流式问答 |
| POST | `/api/chat/stream` | 流式问答（SSE） |

## 测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

测试不依赖 LLM / OCR，可直接运行。

## 规则文件格式

`rules/default_rules.txt` 每行一条，以 `|` 分隔六个字段：

```
一级主题|二级主题|条款编号|条款标题|正文|关联附件
差旅费|住宿标准|T4.1|分城市限额|一线城市：600 元/晚；...|《城市分级住宿标准表》
```

## 致谢与许可

核心实现改编自 [megemini/AuditAgent](https://github.com/megemini/AuditAgent)，原项目采用 Apache License 2.0。本仓库对应模块保留来源说明，后续开发请遵循相同许可。

## 路线图

- 发票去重与最优组合（对齐目标报销金额）
- 报销单 PDF / Excel 台账导出
- 多用户会话与规则库隔离
- 对接钉钉 / 企业微信审批流（AuditAgent 原含钉钉集成，可按需移植）
