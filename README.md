# Presentation Reconstruction Precision

English | [中文](#中文说明)

Presentation Reconstruction Precision is a Codex skill and Python utility set for rebuilding image-based presentation pages into clean, editable PowerPoint decks.

It is designed for cases where a prior image-to-PPT conversion left clipped assets, missing icons, dirty shadows, fused backgrounds, or partially hidden visual objects. The workflow favors editable native PowerPoint shapes where possible, keeps background art separate from foreground content, and runs strict checks before delivery.

## Features

- Reconstruct slide screenshots and exported deck images into editable PPTX files.
- Separate decorative backgrounds from cards, text, icons, photos, charts, and callouts.
- Preserve factual or dense media as rectangular images instead of unsafe transparent cutouts.
- Generate transparent foreground assets with padding and edge-touch integrity checks.
- Audit required component recall so small visible labels and icons are not silently omitted.
- Flag recoverable hidden regions while preventing invented chart data, text, values, or logos.

## Repository Layout

```text
.
├── SKILL.md                  # Codex skill instructions
├── agents/openai.yaml        # Skill display metadata
├── references/               # Reconstruction contracts and schemas
├── scripts/                  # Pipeline and QA utilities
└── requirements.txt          # Python runtime dependencies
```

## Installation

Install the Python dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To use it as a Codex skill, place this repository under your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R presentation-reconstruction-precision ~/.codex/skills/
```

Restart Codex after adding the skill so it can be discovered.

## Basic Usage

Create or bootstrap a semantic deck plan, then run the pipeline:

```bash
python scripts/run_pipeline.py work/deck_plan.json \
  --skip-auto-plan \
  --transparent-mode marked \
  --strict-integrity \
  --out work/reconstructed.pptx
```

The expected planning format is documented in `references/deck_schema.md`. The stricter visual QA expectations are documented in `references/precision_qa_contract.md`.

## Typical Workflow

1. Build `deck_plan.json` and per-slide `layout_plan.json`.
2. Populate `required_components` for every visible text, icon, chart, callout, and important visual block.
3. Mark background art as `background_decor`.
4. Mark foreground assets by role, such as `opaque_icon`, `translucent_subject`, `photo_rect`, or `native_rebuild`.
5. Run the reconstruction pipeline.
6. Inspect previews, checkerboards, mask outputs, recall reports, and integrity reports.
7. Regenerate until strict QA passes or the remaining limitation is explicitly documented.

## License

This project is released under the MIT License. See `LICENSE` for details.

---

# 中文说明

[English](#presentation-reconstruction-precision) | 中文

Presentation Reconstruction Precision 是一个 Codex skill，同时也提供了一组 Python 辅助脚本，用于把基于图片的演示页面、PPT 截图或导出的幻灯片图片，重建为干净、可编辑的 PowerPoint 文件。

它主要解决普通 image-to-PPT 转换中常见的问题：前景素材被裁切、小图标或标签遗漏、阴影和光晕残留、背景和内容粘连、重叠图片中可恢复区域处理不清等。这个工作流尽量使用原生 PowerPoint 对象重建文本、形状、箭头、图表和简单图标，同时把装饰性背景与可编辑前景内容分离，并通过 QA 脚本检查输出质量。

## 功能特点

- 将幻灯片截图、导出的 PPT 图片或页面 mockup 重建为可编辑的 PPTX 文件。
- 将装饰性背景与卡片、文字、图标、照片、图表、标注等内容分离。
- 对含事实信息或内容密集的图片、图表、地图等，保留为矩形图片，避免不安全的透明抠图。
- 为前景透明素材生成安全留白，并检查素材是否贴边或被裁切。
- 检查必要组件是否被完整重建，避免遗漏小标签、小图标和可见标注。
- 对被遮挡但允许恢复的非事实视觉区域进行标记，同时禁止编造图表数据、文字、数值或 logo。

## 仓库结构

```text
.
├── SKILL.md                  # Codex skill 使用说明
├── agents/openai.yaml        # skill 展示信息
├── references/               # 重建规范、QA 合同和 schema
├── scripts/                  # 生成、抠图、导出和 QA 脚本
└── requirements.txt          # Python 依赖
```

## 安装

建议先创建 Python 虚拟环境，再安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果要作为 Codex skill 使用，可以把本仓库放到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R presentation-reconstruction-precision ~/.codex/skills/
```

添加后需要重启 Codex，skill 才能被重新发现。

## 基本用法

先创建或生成语义化的 `deck_plan.json`，然后运行完整流程：

```bash
python scripts/run_pipeline.py work/deck_plan.json \
  --skip-auto-plan \
  --transparent-mode marked \
  --strict-integrity \
  --out work/reconstructed.pptx
```

`deck_plan.json` 的字段格式见 `references/deck_schema.md`。更严格的视觉 QA 要求见 `references/precision_qa_contract.md`。

## 典型流程

1. 创建 `deck_plan.json` 和每页对应的 `layout_plan.json`。
2. 为每一个可见文字、图标、图表、标注和重要视觉块填写 `required_components`。
3. 将纯装饰性背景标记为 `background_decor`。
4. 按角色标记前景素材，例如 `opaque_icon`、`translucent_subject`、`photo_rect` 或 `native_rebuild`。
5. 运行重建流程。
6. 检查预览图、透明素材棋盘格、背景 mask、组件召回报告和完整性报告。
7. 修正计划并重新生成，直到严格 QA 通过，或明确说明仍然存在的限制。

## 许可证

本项目使用 MIT License 开源，详见 `LICENSE`。
