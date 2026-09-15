"""生成曾有为 AI Agent 应用开发岗位简历 PDF。"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(r"E:\AI\repository")
OUTPUT = ROOT / "output" / "pdf" / "曾有为-AI-Agent应用开发.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4

NAVY = colors.HexColor("#123B79")
DEEP_NAVY = colors.HexColor("#0D2F68")
INDIGO = colors.HexColor("#5B5CE2")
CYAN = colors.HexColor("#06A6C7")
TEXT = colors.HexColor("#26364A")
MUTED = colors.HexColor("#607086")
LINE = colors.HexColor("#D8E0EE")
SOFT = colors.HexColor("#F4F7FC")
SOFT_INDIGO = colors.HexColor("#F0F0FF")
WHITE = colors.white


pdfmetrics.registerFont(TTFont("Deng", r"C:\Windows\Fonts\Deng.ttf"))
pdfmetrics.registerFont(TTFont("DengBold", r"C:\Windows\Fonts\Dengb.ttf"))

styles = getSampleStyleSheet()


def style(name: str, **kwargs) -> ParagraphStyle:
    """创建默认支持中文换行的简历文本样式。"""
    defaults = {
        "fontName": "Deng",
        "fontSize": 9.2,
        "leading": 14,
        "textColor": TEXT,
        "wordWrap": "CJK",
    }
    defaults.update(kwargs)
    return ParagraphStyle(
        name,
        parent=styles["Normal"],
        **defaults,
    )


S = {
    "name": style("name", fontName="DengBold", fontSize=28, leading=31, textColor=DEEP_NAVY),
    "subtitle": style("subtitle", fontName="DengBold", fontSize=12.5, leading=17, textColor=INDIGO),
    "contact": style("contact", fontSize=8.8, leading=13, textColor=MUTED, alignment=TA_RIGHT),
    "section": style("section", fontName="DengBold", fontSize=15, leading=19, textColor=DEEP_NAVY),
    "page_title": style("page_title", fontName="DengBold", fontSize=22, leading=27, textColor=DEEP_NAVY),
    "body": style("body", fontSize=9.3, leading=14.5),
    "body_small": style("body_small", fontSize=8.8, leading=13.2),
    "skill_label": style("skill_label", fontName="DengBold", fontSize=9, leading=13, textColor=INDIGO),
    "skill_text": style("skill_text", fontSize=8.8, leading=13),
    "company": style("company", fontName="DengBold", fontSize=10.5, leading=14, textColor=DEEP_NAVY),
    "date": style("date", fontName="DengBold", fontSize=9.4, leading=13, textColor=INDIGO),
    "role": style("role", fontSize=8.7, leading=13, textColor=MUTED, alignment=TA_RIGHT),
    "bullet": style("bullet", fontSize=8.8, leading=13.4, leftIndent=10, firstLineIndent=-8, bulletIndent=0),
    "project_name": style("project_name", fontName="DengBold", fontSize=13.2, leading=17, textColor=DEEP_NAVY),
    "project_badge": style(
        "project_badge",
        fontName="DengBold",
        fontSize=9.2,
        leading=11,
        textColor=WHITE,
        alignment=1,
    ),
    "project_role": style("project_role", fontName="DengBold", fontSize=8.8, leading=13, textColor=INDIGO),
    "project_summary": style("project_summary", fontSize=8.5, leading=12.7, textColor=MUTED),
    "stack": style("stack", fontName="DengBold", fontSize=8.3, leading=12.5, textColor=INDIGO),
    "link": style("link", fontName="DengBold", fontSize=9.2, leading=13, textColor=CYAN),
    "footer": style("footer", fontSize=7.5, leading=10, textColor=colors.HexColor("#96A2B4"), alignment=TA_RIGHT),
}


def p(text: str, key: str = "body") -> Paragraph:
    """创建段落并统一使用简历样式。"""
    return Paragraph(text, S[key])


def section_title(title: str) -> Table:
    """生成带菱形标记和延伸线的分区标题。"""
    table = Table(
        [[p("◆", "section"), p(title, "section"), ""]],
        colWidths=[5 * mm, 31 * mm, 137 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (0, 0), INDIGO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (2, 0), (2, 0), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def bullet(text: str, *, small: bool = False) -> Paragraph:
    """创建紧凑项目符号段落。"""
    return Paragraph(f"•&nbsp;&nbsp;{text}", S["body_small" if small else "bullet"])


def skill_rows() -> Table:
    """生成面向 AI Agent 岗位的核心技能表。"""
    rows = [
        ("Agent 框架", "LangChain、LangGraph、StateGraph、Tool Calling、状态管理、有限重试与降级"),
        ("RAG 工程", "文档解析、Chunking、Embedding、Chroma、Metadata Filter、上下文组装、引用与拒答"),
        ("模型工程", "通义千问、OpenAI-compatible API、多模型路由、查询改写、流式生成、CosyVoice TTS"),
        ("后端开发", "Python、FastAPI、Django / DRF、SQLAlchemy、Alembic、SQLite、MySQL、Redis"),
        ("应用开发", "React、Next.js、TypeScript、Vue 2 / Vue 3、SSE、WebSocket、Web Audio API"),
        ("工程能力", "pytest、Vitest、Ruff、ESLint、Nginx、Uvicorn、日志、请求 ID 与阶段耗时统计"),
    ]
    table = Table(
        [[p(label, "skill_label"), p(text, "skill_text")] for label, text in rows],
        colWidths=[25 * mm, 75 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def experience(date: str, company: str, role: str, bullets: list[str]) -> KeepTogether:
    """生成工作经历区块。"""
    header = Table(
        [[p(date, "date"), p(company, "company"), p(role, "role")]],
        colWidths=[35 * mm, 94 * mm, 44 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return KeepTogether([header, *[bullet(item) for item in bullets], Spacer(1, 3 * mm)])


def project_card(
    number: str,
    title: str,
    meta: str,
    role: str,
    summary: str,
    stack: str,
    bullets: list[str],
    *,
    website: str | None = None,
) -> Table:
    """生成左侧项目信息、右侧技术成果的项目卡片。"""
    badge = Table([[p(number, "project_badge")]], colWidths=[11 * mm], rowHeights=[11 * mm])
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), INDIGO),
                ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0, INDIGO),
            ]
        )
    )
    left = [badge, Spacer(1, 2 * mm), p(meta, "date"), Spacer(1, 2 * mm), p(title, "project_name")]
    left.extend([Spacer(1, 1.5 * mm), p(role, "project_role"), Spacer(1, 1 * mm), p(summary, "project_summary")])
    if website:
        left.extend(
            [
                Spacer(1, 2 * mm),
                p(f'<link href="{website}" color="#06A6C7">{website}</link>', "link"),
            ]
        )
    right = [p(stack, "stack"), Spacer(1, 1.5 * mm), *[bullet(item, small=True) for item in bullets]]
    table = Table(
        [[left, right]],
        colWidths=[47 * mm, 126 * mm],
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.7, LINE),
            ("LINEBEFORE", (0, 0), (0, 0), 2.2, INDIGO),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 7),
            ("RIGHTPADDING", (0, 0), (0, 0), 8),
            ("LEFTPADDING", (1, 0), (1, 0), 10),
            ("RIGHTPADDING", (1, 0), (1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ],
    )
    return table


def page_heading(title: str, subtitle: str) -> Table:
    """生成第二、三页顶部标题。"""
    table = Table(
        [[p(title, "page_title"), p(subtitle, "contact")]],
        colWidths=[112 * mm, 61 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEBELOW", (0, 0), (-1, -1), 1.2, INDIGO),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def draw_page(canvas, doc) -> None:
    """绘制每页顶栏、页码和底部标识。"""
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_HEIGHT - 8 * mm, PAGE_WIDTH, 8 * mm, fill=1, stroke=0)
    canvas.setFont("Deng", 7.5)
    canvas.setFillColor(colors.HexColor("#95A2B6"))
    canvas.drawRightString(PAGE_WIDTH - 15 * mm, 10 * mm, f"{doc.page:02d} / 03")
    canvas.setFillColor(colors.HexColor("#CAD3E1"))
    canvas.drawString(15 * mm, 10 * mm, "AI AGENT APPLICATION DEVELOPMENT")
    canvas.restoreState()


def build() -> None:
    """生成三页可投递简历。"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="曾有为 - AI Agent 应用开发",
        author="曾有为",
        subject="AI Agent 应用开发岗位简历",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="resume", frames=[frame], onPage=draw_page)])

    story = []
    story.append(Spacer(1, 7 * mm))
    contact = (
        "男 · 26 岁 · 深圳<br/>"
        "135 1074 6190<br/>"
        "zengyouwei99@163.com<br/>"
        '<link href="https://notebyzyw.cloud/" color="#06A6C7">notebyzyw.cloud</link>'
    )
    header = Table(
        [
            [p("曾有为", "name"), p(contact, "contact")],
            [p("AI Agent 应用开发 · Python / React / Vue 全栈", "subtitle"), ""],
        ],
        colWidths=[119 * mm, 54 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("SPAN", (1, 0), (1, 1)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LINEBELOW", (0, 1), (-1, 1), 0.8, LINE),
            ]
        )
    )
    story.extend([header, Spacer(1, 6 * mm)])

    overview = [
        section_title("个人概述"),
        Spacer(1, 2 * mm),
        p(
            "近 6 年 Web 与应用开发经验，职业方向聚焦 AI Agent 与 RAG 工程。"
            "具备 LangGraph 工作流、Agent 工具编排、知识库检索、模型流式输出、引用校验、"
            "CosyVoice 实时语音及会话持久化实践；能够使用 Python 构建后端服务，"
            "使用 React / Next.js 与 Vue 构建用户端和管理端，并具备 Java / Spring Boot 项目协作能力。",
            "body",
        ),
    ]
    core = [section_title("核心技能"), Spacer(1, 1 * mm), skill_rows()]
    columns = Table([[overview, core]], colWidths=[68 * mm, 105 * mm])
    columns.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 8),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.extend([columns, Spacer(1, 6 * mm), section_title("工作经历"), Spacer(1, 3 * mm)])
    story.append(
        experience(
            "2024.08 - 至今",
            "深圳市幻影未来科技有限公司",
            "AI Agent 应用开发工程师",
            [
                "参与 AI 虚拟人及智能机器人平台研发，围绕知识库问答与智能终端场景建设文档管理、模型接入、流式回答和运营配置能力。",
                "参与业务知识库的文档导入、分类、审核、同步及多语言配置，支撑知识集中管理、检索问答与终端角色配置。",
                "对接 OpenAI / Azure OpenAI、通义千问、腾讯云及百度千帆等模型服务，统一鉴权、请求参数、流式响应与异常处理。",
                "使用 WebSocket、SSE 与 Redis 串联模型回答、会话上下文、TTS 合成和终端交互，并使用 Vue 完成平台管理端开发。",
            ],
        )
    )
    story.append(
        experience(
            "2021.09 - 2024.07",
            "深圳市科瑞哲科技有限公司",
            "全栈开发工程师",
            [
                "负责网站维护与性能优化，独立开发内部聊天系统，并基于微前端实现和上线小程序模块。",
                "从零构建公司白名单前后端管理系统，将 Python 后端能力用于智能盒子、资源管理与数据接口服务。",
                "主导 Vue 2 至 Vue 3 框架迁移，完善组件、状态管理和接口层，提升团队开发效率与功能扩展能力。",
            ],
        )
    )
    story.append(
        experience(
            "2020.07 - 2021.08",
            "湖南二二三科技有限公司",
            "Web 开发工程师",
            [
                "依据 UI 设计稿完成页面开发、接口对接和移动端适配，通过重构与加载优化改善页面性能。",
                "持续修复线上缺陷并实践 Vue 3 等新技术，为后续全栈和实时应用开发积累工程经验。",
            ],
        )
    )

    story.append(PageBreak())
    story.extend(
        [
            Spacer(1, 8 * mm),
            page_heading("AI Agent 项目经历", "曾有为 · Agent、RAG 与实时交互工程"),
            Spacer(1, 6 * mm),
            project_card(
                "01",
                "ZYW 的 AI 小助理",
                "个人项目 · 在线运行",
                "独立设计与开发",
                "面向访客的个人知识库 Agent，通过自然语言问答介绍 ZYW 的技术能力与项目，并提供可核查引用。",
                "LangGraph · LangChain · FastAPI · 通义千问 · Chroma · SQLite · Next.js · React · SSE · CosyVoice",
                [
                    "使用 LangGraph 定义 Agent 状态与节点，实现规则优先的意图识别、工具选择、检索评价、有限重试、超时与降级退出。",
                    "构建文档加载、清理、结构化切分、哈希去重和稳定片段 ID 链路，以 SQLite 保存权威正文和索引版本，以 Chroma 提供向量召回。",
                    "实现查询改写、Metadata Filter、候选去重、上下文组装、带引用回答和无依据拒答，并区分知识库问答与闲聊模式。",
                    "通过 FastAPI 与 SSE 推送模型增量、Agent 步骤、引用、耗时和推荐追问，支持会话恢复、服务端取消和中断恢复。",
                    "使用 Next.js、React、TypeScript、Tailwind CSS 和 Motion 构建双栏交互界面及管理端，支持文档管理、角色换装和音色配置。",
                    "接入 CosyVoice 回答后实时分句朗读，使用 Web Audio API 驱动精灵嘴部与声波动画。",
                ],
                website="https://notebyzyw.cloud/",
            ),
            Spacer(1, 5 * mm),
            project_card(
                "02",
                "幻科虚拟人及智能机器人管理平台",
                "2024.08 - 至今",
                "AI Agent 应用开发工程师",
                "面向展厅、医院、政务及企业服务场景的 AI 虚拟人与智能终端平台。",
                "OpenAI / Azure OpenAI · 通义千问 · SSE · WebSocket · Redis · TTS · Spring Boot · Vue 2",
                [
                    "围绕知识库问答场景参与文档、分类、问答内容和黑名单等管理能力建设，支持数据导入、审核、同步及多语言配置。",
                    "建设多模型适配链路，统一不同厂商的鉴权参数、调用流程、流式响应和业务异常处理。",
                    "串联知识检索、模型生成、SSE 流式输出和多厂商 TTS，并通过 WebSocket 与智能终端实时通信。",
                    "使用 Redis 维护设备在线状态和会话上下文，支持状态订阅、指令下发与流式消息传递。",
                ],
            ),
            Spacer(1, 5 * mm),
            project_card(
                "03",
                "AI Web 智慧商场与港铁导览平台",
                "2024.08 - 至今",
                "AI 应用全栈协作 · 核心前端",
                "面向商场、港铁站和自助终端的信息服务平台，覆盖室内地图、路线规划与多端适配。",
                "Vue 3 · TypeScript · Pinia · Mappedin · Mapxus · WebSocket · Dijkstra · Vue I18n",
                [
                    "基于 Vue 3、TypeScript 和 Composition API 搭建模块化架构，将地图、楼层、路径、标签和 POI 能力拆分为独立 Composable。",
                    "接入室内地图 SDK，实现 POI 搜索、跨楼层导航、多途经点规划、路径高亮、逐步指引及无障碍路线配置。",
                    "基于 Dijkstra 算法完成港铁路线搜索与候选排序，并建设运行时主题、断线重连和终端交互计时机制。",
                ],
            ),
        ]
    )

    story.append(PageBreak())
    story.extend(
        [
            Spacer(1, 8 * mm),
            page_heading("工程项目经历", "曾有为 · Python / React / Vue 全栈与实时应用"),
            Spacer(1, 6 * mm),
            project_card(
                "01",
                "匿名聊天 Web 版",
                "2022.06 - 2024.07",
                "Web 应用开发",
                "覆盖 Web 与安卓端的加密聊天系统，支持第三方登录、多端消息同步和轻量级小程序模块。",
                "Vue 2 · Vuex · Axios · WebSocket · Vant UI · Element UI · 微前端",
                [
                    "从零搭建 Vue 2 项目框架，完成登录注册等 RESTful 接口通信，并使用 WebSocket 支持双向实时聊天。",
                    "通过 Vuex 管理消息、状态与存储，完成 Web 和移动端适配，并将功能模块化为多个独立小程序。",
                    "使用 CRC32 完成文件校验，支持大文件分片上传、断点续传与传输完整性保障。",
                ],
            ),
            Spacer(1, 5 * mm),
            project_card(
                "02",
                "智能盒子 - 资源管理项目",
                "2023.05 - 2024.07",
                "全栈开发工程师",
                "面向影视、图片和小说资源的集中管理、查询、播放与智能传递平台。",
                "Vue 3 · TypeScript · Element Plus · Vite · Django · DRF · MySQL",
                [
                    "将原 Flask 后端重构为 Django + DRF，实现网盘数据与 MySQL 自动同步，并开发资源爬取与处理模块。",
                    "使用 Vue 3 + TypeScript 构建管理端，封装 Axios 接口层并通过类型定义校验后端返回数据。",
                    "通过代码压缩、按需加载和接口代理改善页面加载速度与项目维护效率。",
                ],
            ),
            Spacer(1, 5 * mm),
            project_card(
                "03",
                "TG 后台与安卓设备管理系统",
                "2021.09 - 2024.07",
                "Web 应用开发",
                "覆盖用户、消息、权限、设备状态、远程操作、日志审计和实时数据分析的管理平台。",
                "Vue 2 / Vue 3 · Pinia / Vuex · Axios · WebSocket · ECharts · Element UI",
                [
                    "从零搭建 Vue 管理端，完成登录、用户、设备和权限等 API 联调，并使用 WebSocket 实时更新消息与设备状态。",
                    "开发分级权限、操作日志和 ECharts 数据可视化模块，支持运行状态与业务数据分析。",
                    "实现 MD5 校验、分片上传与断点续传，兼顾大文件传输效率、完整性和可恢复性。",
                ],
            ),
            Spacer(1, 7 * mm),
            section_title("个人总结"),
            Spacer(1, 3 * mm),
        ]
    )
    summary = Table(
        [
            [
                bullet("具备 LangGraph Agent 工作流、RAG 检索、工具编排、流式输出、引用和拒答等完整项目实践。"),
                bullet("能够使用 Python / FastAPI 构建接口与数据服务，并使用 React、Next.js 和 Vue 构建用户端与管理端。"),
            ],
            [
                bullet("具备多模型适配、SSE、WebSocket、Redis、CosyVoice TTS 与智能终端实时交互经验。"),
                bullet("关注 AI Agent 的可落地、可取消、可观测与可评测，能够从工程基础持续推进到线上部署。"),
            ],
        ],
        colWidths=[86.5 * mm, 86.5 * mm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(summary)

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
