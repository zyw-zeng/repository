"""生成排版更舒展、视觉层级更清晰的 AI Agent 应用开发简历。"""

from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


ROOT = Path(r"E:\AI\repository")
OUTPUT = ROOT / "output" / "pdf" / "曾有为-AI-Agent应用开发.pdf"
W, H = A4

NAVY = colors.HexColor("#12386F")
DEEP = colors.HexColor("#0B2858")
INDIGO = colors.HexColor("#5B5CE2")
CYAN = colors.HexColor("#08A7C7")
TEXT = colors.HexColor("#26364A")
MUTED = colors.HexColor("#66768D")
LINE = colors.HexColor("#DCE4F0")
SOFT = colors.HexColor("#F5F8FC")
SOFT_BLUE = colors.HexColor("#EEF4FF")
SOFT_INDIGO = colors.HexColor("#F2F1FF")
WHITE = colors.white

pdfmetrics.registerFont(TTFont("Deng", r"C:\Windows\Fonts\Deng.ttf"))
pdfmetrics.registerFont(TTFont("DengBold", r"C:\Windows\Fonts\Dengb.ttf"))
pdfmetrics.registerFontFamily("Deng", normal="Deng", bold="DengBold")


def ps(
    name: str,
    size: float,
    leading: float,
    *,
    color=TEXT,
    font="Deng",
    align=TA_LEFT,
    **kwargs,
) -> ParagraphStyle:
    """创建支持中英文混排和中文换行的段落样式。"""
    return ParagraphStyle(
        name,
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        wordWrap="CJK",
        splitLongWords=True,
        **kwargs,
    )


BODY = ps("body", 9.2, 14.2)
BODY_SMALL = ps("body_small", 8.5, 12.8)
BODY_MUTED = ps("body_muted", 8.7, 13.4, color=MUTED)
BULLET = ps("bullet", 8.7, 13.2, leftIndent=10, firstLineIndent=-8)
BULLET_SMALL = ps("bullet_small", 8.25, 12.5, leftIndent=10, firstLineIndent=-8)
CARD_TITLE = ps("card_title", 12.2, 15.5, color=DEEP, font="DengBold")
CARD_META = ps("card_meta", 8.4, 12, color=INDIGO, font="DengBold")
CARD_ROLE = ps("card_role", 8.4, 12, color=MUTED)
STACK = ps("stack", 8.1, 11.6, color=INDIGO, font="DengBold")
MINI_TITLE = ps("mini_title", 9.2, 12.5, color=DEEP, font="DengBold")
MINI_BODY = ps("mini_body", 7.9, 11.5, color=MUTED)


def draw_para(
    canvas: Canvas,
    text: str,
    x: float,
    top: float,
    width: float,
    style: ParagraphStyle = BODY,
) -> float:
    """从指定顶边向下绘制段落，并返回绘制后的纵坐标。"""
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, H)
    paragraph.drawOn(canvas, x, top - height)
    return top - height


def measure(text: str, width: float, style: ParagraphStyle = BODY) -> float:
    """测量段落高度，便于卡片按内容动态确定尺寸。"""
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, H)
    return height


def rounded_card(canvas: Canvas, x: float, y: float, width: float, height: float, *, fill=WHITE) -> None:
    """绘制统一圆角卡片和柔和边框。"""
    canvas.setFillColor(fill)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.7)
    canvas.roundRect(x, y, width, height, 8, fill=1, stroke=1)


def section(canvas: Canvas, title: str, top: float, *, eyebrow: str | None = None) -> float:
    """绘制带栏目编号感的分区标题。"""
    if eyebrow:
        canvas.setFillColor(CYAN)
        canvas.setFont("DengBold", 7.2)
        canvas.drawString(43, top, eyebrow.upper())
        top -= 14
    canvas.setFillColor(INDIGO)
    canvas.circle(47, top + 5, 3, fill=1, stroke=0)
    canvas.setFillColor(DEEP)
    canvas.setFont("DengBold", 15)
    canvas.drawString(58, top, title)
    line_start = 58 + pdfmetrics.stringWidth(title, "DengBold", 15) + 12
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.8)
    canvas.line(line_start, top + 5, W - 43, top + 5)
    return top - 19


def page_chrome(canvas: Canvas, page: int, label: str) -> None:
    """绘制统一顶栏、页脚和页码。"""
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 9, W, 9, fill=1, stroke=0)
    canvas.setFont("Deng", 7)
    canvas.setFillColor(colors.HexColor("#B8C7DC"))
    canvas.drawString(43, 24, label.upper())
    canvas.setFillColor(colors.HexColor("#8C9AAF"))
    canvas.drawRightString(W - 43, 24, f"{page:02d} / 03")


def draw_tag(canvas: Canvas, text: str, x: float, y: float, *, selected: bool = False) -> float:
    """绘制紧凑技能标签并返回下一个横坐标。"""
    text_width = pdfmetrics.stringWidth(text, "Deng", 7.7)
    width = text_width + 16
    canvas.setFillColor(INDIGO if selected else SOFT_INDIGO)
    canvas.setStrokeColor(INDIGO if selected else LINE)
    canvas.roundRect(x, y, width, 19, 9.5, fill=1, stroke=1)
    canvas.setFillColor(WHITE if selected else DEEP)
    canvas.setFont("Deng", 7.7)
    canvas.drawCentredString(x + width / 2, y + 6.1, text)
    return x + width + 6


def capability_card(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    title: str,
    content: str,
    number: str,
) -> None:
    """绘制首页核心能力小卡。"""
    rounded_card(canvas, x, y, width, 53, fill=SOFT)
    canvas.setFillColor(INDIGO)
    canvas.setFont("DengBold", 7.2)
    canvas.drawString(x + 10, y + 36, number)
    draw_para(canvas, title, x + 29, y + 44, width - 39, MINI_TITLE)
    draw_para(canvas, content, x + 10, y + 25, width - 20, MINI_BODY)


def work_card(
    canvas: Canvas,
    top: float,
    date: str,
    company: str,
    role: str,
    points: list[str],
    height: float,
) -> float:
    """绘制留白清楚的工作经历卡片。"""
    x, width = 43, W - 86
    bottom = top - height
    rounded_card(canvas, x, bottom, width, height, fill=WHITE)
    canvas.setFillColor(INDIGO)
    canvas.roundRect(x, bottom, 4, height, 2, fill=1, stroke=0)
    canvas.setFont("DengBold", 8.6)
    canvas.drawString(x + 14, top - 19, date)
    canvas.setFillColor(DEEP)
    canvas.setFont("DengBold", 10.3)
    canvas.drawString(x + 112, top - 19, company)
    canvas.setFillColor(MUTED)
    canvas.setFont("Deng", 8.2)
    canvas.drawRightString(x + width - 14, top - 19, role)
    y = top - 37
    for point in points:
        y = draw_para(canvas, f"•&nbsp;&nbsp;{point}", x + 14, y, width - 28, BULLET)
        y -= 2
    return bottom - 9


def draw_qr(canvas: Canvas, value: str, x: float, y: float, size: float) -> None:
    """绘制可扫描的网站二维码。"""
    qr = QrCodeWidget(value)
    bounds = qr.getBounds()
    scale = size / max(bounds[2] - bounds[0], bounds[3] - bounds[1])
    drawing = Drawing(size, size, transform=[scale, 0, 0, scale, 0, 0])
    drawing.add(qr)
    renderPDF.draw(drawing, canvas, x, y)


def project_card(
    canvas: Canvas,
    top: float,
    number: str,
    title: str,
    meta: str,
    role: str,
    summary: str,
    stack: str,
    points: list[str],
    height: float,
    *,
    hero: bool = False,
    website: str | None = None,
) -> float:
    """绘制项目卡；核心个人项目使用更强的双栏视觉。"""
    x, width = 43, W - 86
    bottom = top - height
    rounded_card(canvas, x, bottom, width, height, fill=WHITE if not hero else colors.HexColor("#FBFCFF"))
    canvas.setFillColor(CYAN if hero else INDIGO)
    canvas.roundRect(x, bottom, 4, height, 2, fill=1, stroke=0)
    left_width = 145 if hero else 151
    divider_x = x + left_width
    canvas.setStrokeColor(LINE)
    canvas.line(divider_x, bottom + 13, divider_x, top - 13)

    canvas.setFillColor(INDIGO)
    canvas.roundRect(x + 14, top - 43, 34, 29, 5, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("DengBold", 8.5)
    canvas.drawCentredString(x + 31, top - 32, number)
    y_left = top - 59
    y_left = draw_para(canvas, meta, x + 14, y_left, left_width - 28, CARD_META) - 7
    y_left = draw_para(canvas, title, x + 14, y_left, left_width - 28, CARD_TITLE) - 4
    y_left = draw_para(canvas, role, x + 14, y_left, left_width - 28, CARD_META) - 5
    y_left = draw_para(canvas, summary, x + 14, y_left, left_width - 28, BODY_MUTED)

    if website:
        draw_qr(canvas, website, x + 14, bottom + 22, 46)
        canvas.setFillColor(CYAN)
        canvas.setFont("DengBold", 7.8)
        canvas.drawString(x + 67, bottom + 53, "在线访问")
        canvas.setFont("Deng", 7.1)
        canvas.drawString(x + 67, bottom + 38, "notebyzyw.cloud")
        canvas.linkURL(website, (x + 14, bottom + 18, divider_x - 12, bottom + 72), relative=0)

    right_x = divider_x + 14
    right_width = width - left_width - 28
    y = draw_para(canvas, stack, right_x, top - 18, right_width, STACK) - 7
    for point in points:
        y = draw_para(canvas, f"•&nbsp;&nbsp;{point}", right_x, y, right_width, BULLET_SMALL if hero else BULLET)
        y -= 3
    return bottom - 11


def mini_feature(canvas: Canvas, x: float, y: float, width: float, title: str, text: str) -> None:
    """绘制工程亮点摘要卡。"""
    rounded_card(canvas, x, y, width, 67, fill=SOFT)
    canvas.setFillColor(CYAN)
    canvas.circle(x + 14, y + 49, 3, fill=1, stroke=0)
    draw_para(canvas, title, x + 24, y + 57, width - 34, MINI_TITLE)
    draw_para(canvas, text, x + 12, y + 36, width - 24, MINI_BODY)


def header_page_one(canvas: Canvas) -> None:
    """绘制首页姓名、定位与联系方式。"""
    canvas.setFillColor(DEEP)
    canvas.setFont("DengBold", 27)
    canvas.drawString(43, 773, "曾有为")
    canvas.setFillColor(INDIGO)
    canvas.setFont("DengBold", 12.5)
    canvas.drawString(43, 749, "AI Agent 应用开发")
    canvas.setFillColor(MUTED)
    canvas.setFont("Deng", 8.7)
    canvas.drawString(173, 751, "Python / React / Vue 全栈")

    canvas.setFont("Deng", 8.3)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(W - 43, 775, "深圳 · 26 岁")
    canvas.drawRightString(W - 43, 759, "135 1074 6190  ·  zengyouwei99@163.com")
    canvas.setFillColor(CYAN)
    canvas.setFont("DengBold", 8.3)
    canvas.drawRightString(W - 43, 743, "notebyzyw.cloud")
    canvas.linkURL("https://notebyzyw.cloud/", (W - 135, 737, W - 43, 752), relative=0)
    canvas.setStrokeColor(LINE)
    canvas.line(43, 729, W - 43, 729)


def page_one(canvas: Canvas) -> None:
    """第一页：定位、核心能力和工作经历。"""
    page_chrome(canvas, 1, "AI Agent Application Development")
    header_page_one(canvas)
    top = section(canvas, "定位与核心能力", 703, eyebrow="Profile")

    rounded_card(canvas, 43, top - 177, 205, 177, fill=SOFT_BLUE)
    canvas.setFillColor(DEEP)
    canvas.setFont("DengBold", 10.3)
    canvas.drawString(57, top - 24, "从 Web 全栈走向 Agent 工程")
    draw_para(
        canvas,
        "近 6 年 Web 与应用开发经验，职业方向聚焦 <b>AI Agent 与 RAG 工程</b>。"
        "具备 Agent 工作流、工具编排、知识库检索、流式输出、引用校验、实时语音和会话持久化实践。",
        57,
        top - 43,
        177,
        BODY,
    )
    canvas.setFillColor(CYAN)
    canvas.setFont("DengBold", 7.3)
    canvas.drawString(57, top - 139, "当前方向")
    tag_x = draw_tag(canvas, "Agent", 57, top - 166, selected=True)
    tag_x = draw_tag(canvas, "RAG", tag_x, top - 166)
    draw_tag(canvas, "实时交互", tag_x, top - 166)

    cap_x, cap_w = 260, (W - 43 - 260 - 8) / 2
    capability_card(canvas, cap_x, top - 53, cap_w, "Agent 框架", "LangGraph、LangChain、工具调用与状态管理", "01")
    capability_card(canvas, cap_x + cap_w + 8, top - 53, cap_w, "RAG 工程", "切分、向量检索、引用、拒答与评估", "02")
    capability_card(canvas, cap_x, top - 115, cap_w, "模型与实时", "多模型适配、SSE、WebSocket、CosyVoice", "03")
    capability_card(canvas, cap_x + cap_w + 8, top - 115, cap_w, "全栈开发", "FastAPI、React、Next.js、Vue、SQLAlchemy", "04")
    capability_card(canvas, cap_x, top - 177, cap_w, "数据与存储", "SQLite、MySQL、Redis、Chroma、文件存储", "05")
    capability_card(canvas, cap_x + cap_w + 8, top - 177, cap_w, "工程质量", "pytest、Vitest、日志、耗时与部署", "06")

    work_top = section(canvas, "工作经历", top - 211, eyebrow="Experience")
    work_top = work_card(
        canvas,
        work_top,
        "2024.08 - 至今",
        "深圳市幻影未来科技有限公司",
        "AI Agent 应用开发工程师",
        [
            "参与 AI 虚拟人及智能机器人平台研发，建设知识库问答、模型接入、流式回答与运营配置能力。",
            "统一 OpenAI / Azure OpenAI、通义千问等模型的鉴权、请求参数、SSE 流式响应和异常处理。",
            "使用 WebSocket、SSE 与 Redis 串联模型回答、会话上下文、TTS 合成和终端实时交互。",
        ],
        108,
    )
    work_top = work_card(
        canvas,
        work_top,
        "2021.09 - 2024.07",
        "深圳市科瑞哲科技有限公司",
        "全栈开发工程师",
        [
            "独立开发内部聊天系统和公司白名单管理系统，将 Python 后端用于智能盒子、资源管理与数据接口服务。",
            "主导 Vue 2 至 Vue 3 框架迁移，完善组件、状态管理和接口层，提升开发效率与扩展能力。",
        ],
        86,
    )
    work_card(
        canvas,
        work_top,
        "2020.07 - 2021.08",
        "湖南二二三科技有限公司",
        "Web 开发工程师",
        ["完成页面开发、接口对接和移动端适配，通过重构与加载优化持续改善页面性能。"],
        62,
    )


def page_two(canvas: Canvas) -> None:
    """第二页：突出个人 Agent 项目和 AI 业务项目。"""
    page_chrome(canvas, 2, "Selected AI Agent Projects")
    top = section(canvas, "AI Agent 项目经历", 775, eyebrow="Selected Projects")
    top = project_card(
        canvas,
        top,
        "01",
        "ZYW 的 AI 小助理",
        "个人项目 · 在线运行",
        "独立设计与开发",
        "面向访客的个人知识库 Agent，通过自然语言问答介绍 ZYW 的技术能力与项目，并提供可核查来源。",
        "LangGraph · LangChain · FastAPI · 通义千问 · Chroma · SQLite · Next.js · React · SSE · CosyVoice",
        [
            "<b>Agent 工作流：</b>规则优先的意图识别、工具选择、检索评价、有限重试、超时和降级退出。",
            "<b>可靠 RAG：</b>文档解析、结构化切分、稳定片段 ID、向量召回、Metadata Filter、引用与无依据拒答。",
            "<b>实时交互：</b>SSE 推送模型增量、Agent 步骤、引用、耗时和推荐追问，支持服务端取消与中断恢复。",
            "<b>会话与管理：</b>持久化会话和运行记录，提供文档上传、状态、删除、重建索引与音色配置。",
            "<b>角色语音：</b>CosyVoice 实时分句朗读，使用 Web Audio API 驱动精灵嘴部与声波动画。",
        ],
        270,
        hero=True,
        website="https://notebyzyw.cloud/",
    )
    top = project_card(
        canvas,
        top,
        "02",
        "幻科虚拟人及智能机器人管理平台",
        "2024.08 - 至今",
        "AI Agent 应用开发工程师",
        "面向展厅、医院、政务及企业服务场景的 AI 虚拟人与智能终端平台。",
        "OpenAI / Azure OpenAI · 通义千问 · SSE · WebSocket · Redis · TTS · Spring Boot · Vue",
        [
            "参与知识库文档、分类、问答内容及多语言配置能力建设，支撑集中管理与检索问答。",
            "建设多模型适配链路，统一不同厂商的鉴权、调用流程、流式响应和异常处理。",
            "串联知识检索、模型生成、SSE、TTS 与终端通信，并使用 Redis 维护状态和会话上下文。",
        ],
        166,
    )
    project_card(
        canvas,
        top,
        "03",
        "AI Web 智慧商场与港铁导览平台",
        "2024.08 - 至今",
        "AI 应用全栈协作 · 核心前端",
        "多终端室内地图导览平台，支持路线规划与多语言。",
        "Vue 3 · TypeScript · Pinia · Mappedin · Mapxus · WebSocket · Dijkstra · Vue I18n",
        [
            "以 Composition API 拆分地图、楼层、路径、标签和 POI 能力，建设可维护的模块化架构。",
            "实现 POI 搜索、跨楼层导航、多途经点规划、路径高亮、逐步指引与无障碍路线配置。",
            "基于 Dijkstra 完成路线搜索与排序，并建设主题、断线重连和终端交互计时机制。",
        ],
        165,
    )


def page_three(canvas: Canvas) -> None:
    """第三页：工程项目证明和岗位匹配总结。"""
    page_chrome(canvas, 3, "Engineering Projects and Strengths")
    top = section(canvas, "工程项目经历", 775, eyebrow="Engineering Projects")
    top = project_card(
        canvas,
        top,
        "01",
        "匿名聊天 Web 版",
        "2022.06 - 2024.07",
        "Web 应用开发",
        "Web 与安卓端加密聊天，支持登录、多端同步与小程序。",
        "Vue 2 · Vuex · Axios · WebSocket · Vant UI · Element UI · 微前端",
        [
            "从零搭建 Vue 2 项目，完成 RESTful 接口通信，并使用 WebSocket 支持双向实时聊天。",
            "将 Web 功能模块化为多个独立小程序，支持生态隔离与互通。",
            "使用 CRC32 完成文件校验，支持大文件分片上传和断点续传。",
        ],
        146,
    )
    top = project_card(
        canvas,
        top,
        "02",
        "智能盒子 - 资源管理项目",
        "2023.05 - 2024.07",
        "全栈开发工程师",
        "影视、图片与小说资源管理平台。",
        "Vue 3 · TypeScript · Element Plus · Vite · Django · DRF · MySQL",
        [
            "将 Flask 后端重构为 Django + DRF，实现网盘数据与 MySQL 自动同步。",
            "开发资源爬取与处理模块，并使用 Vue 3 + TypeScript 构建管理端和类型化接口层。",
            "通过代码压缩、按需加载和 API 代理改善页面速度与维护效率。",
        ],
        146,
    )
    top = project_card(
        canvas,
        top,
        "03",
        "TG 后台与安卓设备管理系统",
        "2021.09 - 2024.07",
        "Web 应用开发",
        "覆盖用户、消息、权限、设备状态、日志审计和实时数据分析。",
        "Vue 2 / Vue 3 · Pinia / Vuex · Axios · WebSocket · ECharts · Element UI",
        [
            "从零搭建管理端并完成用户、设备和权限 API 联调，使用 WebSocket 实时更新状态。",
            "开发分级权限、操作日志与 ECharts 可视化模块，支持状态和业务数据分析。",
            "实现 MD5 校验、分片上传与断点续传，保障大文件传输完整性和可恢复性。",
        ],
        164,
    )

    feature_top = section(canvas, "岗位匹配亮点", top - 2, eyebrow="Strengths")
    card_y = feature_top - 67
    gap = 8
    card_w = (W - 86 - gap * 2) / 3
    mini_feature(canvas, 43, card_y, card_w, "能独立完成闭环", "从后端、Agent、RAG 到 React 界面、TTS 和线上部署。")
    mini_feature(canvas, 43 + card_w + gap, card_y, card_w, "重视可靠性", "引用、拒答、有限重试、任务取消、恢复和数据一致性。")
    mini_feature(canvas, 43 + (card_w + gap) * 2, card_y, card_w, "具备实时经验", "SSE、WebSocket、Redis、流式模型输出与智能终端交互。")

    summary_top = section(canvas, "个人总结", card_y - 26)
    rounded_card(canvas, 43, summary_top - 74, W - 86, 74, fill=SOFT_BLUE)
    draw_para(
        canvas,
        "具备 <b>LangGraph Agent 工作流、RAG 检索、工具编排、流式输出、引用与拒答</b>的完整项目实践。"
        "能够使用 Python / FastAPI 构建接口与数据服务，使用 React、Next.js 和 Vue 构建用户端与管理端；"
        "关注 AI Agent 的可落地、可取消、可观测和可评测，并具备将项目持续推进到线上部署的能力。",
        57,
        summary_top - 15,
        W - 114,
        BODY,
    )


def build() -> None:
    """创建三页美化版简历并写入稳定输出路径。"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(
        str(OUTPUT),
        pagesize=A4,
        pageCompression=1,
    )
    canvas.setTitle("曾有为 - AI Agent 应用开发")
    canvas.setAuthor("曾有为")
    canvas.setSubject("AI Agent 应用开发岗位简历")

    for draw_page in (page_one, page_two, page_three):
        draw_page(canvas)
        canvas.showPage()
    canvas.save()
    print(OUTPUT)


if __name__ == "__main__":
    build()
