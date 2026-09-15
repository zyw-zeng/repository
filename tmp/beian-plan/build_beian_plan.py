"""生成湖南省个人网站备案所需的网站建设方案书及提交说明。"""

from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


REFERENCE = Path(r"C:\Users\Administrator\Downloads\网站建设方案书（个人）.docx")
OUTPUT_DIR = Path(r"E:\AI\repository\output\备案资料")
FINAL_DOCX = OUTPUT_DIR / "网站建设方案书-曾有为.docx"
GUIDE_TXT = OUTPUT_DIR / "备案提交说明-曾有为.txt"
DIAGRAM = Path(r"E:\AI\repository\tmp\beian-plan\网站界面与技术架构示意图.png")

FONT_NAME = "仿宋"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def set_cell_shading(cell, fill: str) -> None:
    """设置表格单元格底色。"""
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120) -> None:
    """统一表格单元格内边距。"""
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def style_run(run, size: float = 14, bold: bool = False, color: str = "222222") -> None:
    """设置中文正文运行格式。"""
    run.font.name = FONT_NAME
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_NAME)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def style_paragraph(paragraph, *, first_line: bool = True, after: float = 6) -> None:
    """设置正文段落节奏。"""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    paragraph.paragraph_format.space_after = Pt(after)
    paragraph.paragraph_format.first_line_indent = Pt(28) if first_line else None


def add_text(document, text: str, *, bold_prefix: str | None = None, first_line: bool = True) -> None:
    """添加普通正文，可将开头标签加粗。"""
    paragraph = document.add_paragraph()
    style_paragraph(paragraph, first_line=first_line)
    if bold_prefix and text.startswith(bold_prefix):
        lead = paragraph.add_run(bold_prefix)
        style_run(lead, bold=True)
        rest = paragraph.add_run(text[len(bold_prefix):])
        style_run(rest)
    else:
        run = paragraph.add_run(text)
        style_run(run)


def add_heading(document, title: str) -> None:
    """添加与原模板一致的章节标题。"""
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(title)
    style_run(run, size=16, bold=True, color="111111")


def add_bullet(document, text: str) -> None:
    """添加紧凑的监管说明条目。"""
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Pt(24)
    paragraph.paragraph_format.first_line_indent = Pt(-12)
    paragraph.paragraph_format.line_spacing = 1.35
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run(f"• {text}")
    style_run(run, size=13.5)


def create_diagram(path: Path) -> None:
    """绘制网站界面和技术架构示意图，满足方案书设计图要求。"""
    width, height = 1600, 950
    image = Image.new("RGB", (width, height), "#F5F7FB")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype(str(FONT_PATH), 48)
    heading_font = ImageFont.truetype(str(FONT_PATH), 32)
    body_font = ImageFont.truetype(str(FONT_PATH), 25)
    small_font = ImageFont.truetype(str(FONT_PATH), 21)

    draw.rounded_rectangle((40, 35, 1560, 915), radius=28, fill="#FFFFFF", outline="#CBD5E1", width=3)
    draw.text((80, 65), "notebyzyw.cloud 网站界面与技术架构示意图", font=title_font, fill="#172033")

    # 左侧展示网站单屏双栏界面结构。
    draw.rounded_rectangle((80, 155, 805, 850), radius=22, fill="#0B1020", outline="#46506A", width=3)
    draw.text((115, 185), "访客页面（单屏双栏）", font=heading_font, fill="#E8ECFF")
    draw.rounded_rectangle((115, 250, 390, 790), radius=20, fill="#151D35", outline="#6273B9", width=2)
    draw.text((175, 295), "AI 精灵舞台", font=body_font, fill="#AFC0FF")
    draw.ellipse((185, 390, 325, 530), fill="#7C6DFF", outline="#B8B1FF", width=4)
    draw.text((175, 590), "状态 / 语音 / 动画", font=small_font, fill="#D6DBF1")
    draw.rounded_rectangle((420, 250, 770, 790), radius=20, fill="#11182C", outline="#6273B9", width=2)
    draw.text((510, 295), "智能聊天", font=body_font, fill="#AFC0FF")
    for index, label in enumerate(("访客提问", "Agent 检索", "引用回答", "推荐追问")):
        top = 380 + index * 82
        draw.rounded_rectangle((460, top, 730, top + 52), radius=16, fill="#202B49")
        draw.text((520, top + 11), label, font=small_font, fill="#EEF1FF")

    # 右侧展示实际部署链路。
    draw.rounded_rectangle((850, 155, 1520, 850), radius=22, fill="#EEF2FF", outline="#AAB7E8", width=3)
    draw.text((1025, 185), "访问与部署链路", font=heading_font, fill="#27355D")
    boxes = [
        ("浏览器 / 手机", "HTTPS 访问"),
        ("Nginx 反向代理", "证书、限流、日志"),
        ("Next.js 前端", "React + TypeScript"),
        ("FastAPI 服务", "LangGraph Agent / SSE"),
        ("个人知识库", "SQLite + Chroma"),
    ]
    y = 275
    for index, (name, desc) in enumerate(boxes):
        draw.rounded_rectangle((970, y, 1400, y + 82), radius=18, fill="#FFFFFF", outline="#7486CC", width=2)
        draw.text((1010, y + 12), name, font=body_font, fill="#243257")
        draw.text((1010, y + 48), desc, font=small_font, fill="#5B6785")
        if index < len(boxes) - 1:
            draw.line((1185, y + 82, 1185, y + 112), fill="#6678BE", width=5)
            draw.polygon(((1175, y + 105), (1195, y + 105), (1185, y + 118)), fill="#6678BE")
        y += 116

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=95)


def clear_document_body(document: Document) -> None:
    """移除模板正文，保留节设置、样式和其他包部件。"""
    body = document._element.body
    section_properties = body.sectPr
    for child in list(body):
        if child is not section_properties:
            body.remove(child)


def configure_styles(document: Document) -> None:
    """设置模板沿用的中文字体与页面参数。"""
    normal = document.styles["Normal"]
    normal.font.name = FONT_NAME
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_NAME)
    normal.font.size = Pt(14)
    for section in document.sections:
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.05)
        section.right_margin = Inches(1.05)


def add_cover(document: Document) -> None:
    """添加封面与基础备案信息。"""
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(10)
    title.paragraph_format.space_after = Pt(24)
    run = title.add_run("网站建设方案")
    style_run(run, size=22, bold=True, color="111111")

    info = [
        ("备案主办者", "曾有为"),
        ("新增服务名称", "曾有为的个人技术展示"),
        ("网站展示名称", "ZYW 的 AI 小助理"),
        ("新增域名", "notebyzyw.cloud"),
        ("网站性质", "个人非经营性网站"),
        ("接入服务商", "腾讯云计算（北京）有限责任公司广州分公司"),
    ]
    table = document.add_table(rows=len(info), cols=2)
    table.autofit = False
    table.columns[0].width = Cm(4.2)
    table.columns[1].width = Cm(10.6)
    for row_index, (label, value) in enumerate(info):
        left, right = table.rows[row_index].cells
        set_cell_shading(left, "EEF2F7")
        for cell in (left, right):
            set_cell_margins(cell)
        left_p = left.paragraphs[0]
        left_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_run(left_p.add_run(label), size=13.5, bold=True)
        right_p = right.paragraphs[0]
        style_run(right_p.add_run(value), size=13.5)

    note = document.add_paragraph()
    note.paragraph_format.space_before = Pt(18)
    note.paragraph_format.line_spacing = 1.5
    note.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    style_run(note.add_run("方案说明："), size=13.5, bold=True)
    style_run(
        note.add_run(
            "本方案用于 notebyzyw.cloud 新增网站服务备案。网站由本人建设并维护，主要用于展示个人技术经历、"
            "软件开发作品与个人公开知识库，并通过“ZYW 的 AI 小助理”提供围绕本人公开资料的智能问答。"
            "网站不开展经营性收费，不设置公众信息发布、论坛、新闻采编、网络交易、医疗、金融、教育培训、"
            "视听节目或其他需要前置审批的服务。"
        ),
        size=13.5,
    )

    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_main_content(document: Document) -> None:
    """写入完整的网站建设与安全管理方案。"""
    add_heading(document, "一、网站内容及栏目介绍")
    add_text(
        document,
        "1. 建站目的与服务对象：网站用于个人技术作品展示和职业交流，面向希望了解曾有为本人技术能力、项目经历及“ZYW 的 AI 小助理”项目的访客。网站内容以本人原创项目资料、本人简历和本人整理的技术说明为主，不代表任何企业或机构。",
        bold_prefix="1. 建站目的与服务对象：",
    )
    add_text(
        document,
        "2. 页面结构：访客端采用单屏双栏结构，左侧为 AI 精灵展示区，用于呈现待机、思考、回答和语音播放状态；右侧为智能聊天区，用于输入问题、查看流式回答、引用来源、推荐追问和对话时间。移动端使用独立布局，保留聊天主功能并将精灵缩小为可交互组件。",
        bold_prefix="2. 页面结构：",
    )
    add_text(
        document,
        "3. 主要栏目及功能：",
        bold_prefix="3. 主要栏目及功能：",
    )
    for item in (
        "个人介绍：展示本人姓名、个人简介、技术方向、开发经历和联系方式范围内的公开信息。",
        "项目介绍：展示“ZYW 的 AI 小助理”的建设背景、核心功能、技术架构、开发过程和演示入口。",
        "智能问答：访客可就曾有为的技术能力、项目经历和公开资料进行提问；系统通过个人知识库检索、生成回答并展示引用来源。普通问候可进入闲聊模式。",
        "岗位匹配：访客可粘贴岗位描述，系统将岗位要求拆分后与本人公开经历进行证据匹配，生成仅供参考的匹配报告，不提供招聘中介或收费服务。",
        "简历预览与下载：展示并下载本人主动公开的简历文件，不允许访客上传或发布简历。",
        "语音朗读与角色状态：系统可使用合成语音朗读回答，访客可停止播放；AI 精灵状态仅用于改善交互体验。",
        "管理端：仅供本人登录，用于上传和维护个人知识库文档、控制公开范围、重新索引、查看处理状态以及配置角色音色；不向普通访客开放。",
    ):
        add_bullet(document, item)
    add_text(
        document,
        "4. 内容边界：网站不开放公众注册、评论、发帖、直播或用户内容公开发布功能；访客输入仅用于当前问答或岗位匹配，不会自动公开。智能回答仅围绕本人公开资料和一般性闲聊，不生成或传播法律法规禁止的内容。涉及本人经历和项目事实的问题优先依据知识库作答，无充分依据时明确提示无法确认。",
        bold_prefix="4. 内容边界：",
    )
    add_text(
        document,
        "5. 域名用途与拓展：本次仅使用 notebyzyw.cloud 对外提供上述个人网站服务，不将该域名转让、出租或用于其他主体。后续如增加子域名，仅用于同一备案主体下的静态资源、接口或管理功能，并在上线前检查是否需要变更备案；如业务性质、服务名称或内容范围发生实质变化，将依法先办理备案变更或相关审批。",
        bold_prefix="5. 域名用途与拓展：",
    )

    document.add_picture(str(DIAGRAM), width=Cm(15.9))
    caption = document.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(8)
    style_run(caption.add_run("图 1  notebyzyw.cloud 网站界面与技术架构设计示意图"), size=11.5, color="5B6475")

    add_heading(document, "二、人员及资金安排")
    add_text(
        document,
        "1. 人员安排：网站由备案主办者曾有为个人建设、运营和维护。本人具备约 6 年 Web 应用开发经验，熟悉 Python、FastAPI、React、TypeScript、数据库、RAG 知识库、LangChain/LangGraph Agent、SSE 流式交互和基础服务器运维，可独立完成内容维护、程序升级、日志检查、故障处理和安全配置。网站不设编辑部、新闻采编团队或商业运营团队。",
        bold_prefix="1. 人员安排：",
    )
    add_text(
        document,
        "2. 职责分工：本人同时担任网站负责人、域名负责人、内容审核负责人和安全联系人。新增公开资料由本人核对来源、隐私和版权后发布；程序更新由本人在测试环境验证后部署；发现违法违规、侵权、隐私泄露或安全异常时，由本人立即下线相关内容或功能并处置。",
        bold_prefix="2. 职责分工：",
    )
    add_text(
        document,
        "3. 资金安排：建设和运行费用由本人使用个人自有资金承担，主要包括域名续费、腾讯云服务器、HTTPS 证书、数据备份、模型接口调用和必要的软件服务费用。网站当前不收费、不融资、不接受商业广告，不开展商品或服务交易；根据实际访问量控制资源规格和接口额度，保证域名、服务器及安全维护费用持续可支付。",
        bold_prefix="3. 资金安排：",
    )

    add_heading(document, "三、内容管理制度（设备、组网、技术和部署）")
    add_text(
        document,
        "1. 设备与部署：网站部署于本次备案订单关联的腾讯云中国大陆地域云服务器，使用 Linux 操作系统、宝塔面板和 Nginx。公网访问仅开放网站服务所需端口；Next.js 前端服务和 FastAPI 后端服务监听本机回环地址，由 Nginx 统一通过 HTTPS 反向代理，不直接暴露数据库和向量库端口。服务器实例地域、配置和公网 IP 以腾讯云备案订单及控制台实际信息为准。",
        bold_prefix="1. 设备与部署：",
    )
    add_text(
        document,
        "2. 组网结构：访问链路为“访客浏览器或手机 - HTTPS - Nginx - Next.js 前端/FastAPI 接口 - 应用服务 - SQLite 与 Chroma 数据存储”。后台管理接口与访客接口分离，管理操作必须通过 FastAPI 鉴权；模型调用由后端发起，浏览器端不保存云模型密钥。",
        bold_prefix="2. 组网结构：",
    )
    add_text(
        document,
        "3. 使用技术：前端采用 Next.js、React、TypeScript 和 Tailwind CSS；后端采用 Python、FastAPI、LangGraph/LangChain；知识库使用 SQLite 保存权威文档与切片信息，Chroma 保存向量索引；聊天采用 SSE 流式返回；语音朗读接入阿里云 CosyVoice；模型能力通过服务层封装并配置超时、重试、取消和错误降级。",
        bold_prefix="3. 使用技术：",
    )
    add_text(
        document,
        "4. 内容来源与发布：公开内容仅来自本人简历、本人项目文档、本人撰写的说明和本人有权公开的资料，不自动采集新闻、不镜像第三方网站。知识库文档由本人通过管理端上传，先校验文件类型和大小，再进行解析、切分、去重、索引和可见性设置；只有明确设为公开的资料才能用于访客问答。",
        bold_prefix="4. 内容来源与发布：",
    )
    add_text(
        document,
        "5. 日常维护：本人至少每周检查运行日志、错误记录、模型费用和异常访问情况，每月检查系统更新、依赖安全补丁、备份可恢复性和域名/证书状态。重要配置变更前备份，更新后验证首页、聊天、引用、下载、管理登录和移动端访问。失效、错误或不宜公开的资料及时删除并清理对应索引。",
        bold_prefix="5. 日常维护：",
    )

    add_heading(document, "四、网站安全与信息安全管理制度")
    add_text(
        document,
        "1. 网络安全防御：全站使用 HTTPS；Nginx 负责证书、访问日志、请求大小限制、超时和必要的访问频率限制；云服务器安全组仅开放必要端口；管理端使用独立令牌鉴权并定期更换；系统密钥存放在服务器环境变量文件中且禁止通过网站公开下载。定期更新操作系统和依赖，及时修复高风险漏洞。",
        bold_prefix="1. 网络安全防御：",
    )
    add_text(
        document,
        "2. 应用与接口安全：上传接口限制文件格式、大小和管理权限；数据库操作使用参数化方式和统一存储层；接口设置请求标识、统一异常处理、超时、有限重试和任务取消，防止无限循环与资源占用。聊天和 Agent 工具仅调用服务层允许的能力，不能直接任意访问服务器文件、数据库或执行系统命令。",
        bold_prefix="2. 应用与接口安全：",
    )
    add_text(
        document,
        "3. 内容与生成式人工智能管理：网站明确标识 AI 生成内容可能存在误差。涉及本人经历、项目和简历的回答必须先检索公开知识库，引用正文从有效文档版本读取并校验归属；检索不到可靠证据时拒绝编造。系统区分知识问答与普通闲聊，禁止将访客提示当作后台指令执行。本人定期抽查回答和引用，发现错误立即修正文档、提示词或规则。",
        bold_prefix="3. 内容与生成式人工智能管理：",
    )
    add_text(
        document,
        "4. 个人信息与数据管理：网站遵循最小必要原则，不要求访客注册，不主动收集身份证件、银行卡等敏感信息。访客不得在提问或岗位描述中提交敏感个人信息；运行日志仅用于故障和安全分析，限制后台访问并按维护需要定期清理。简历仅展示本人主动公开的信息，原始管理资料默认不公开。",
        bold_prefix="4. 个人信息与数据管理：",
    )
    add_text(
        document,
        "5. 备份与权限：应用配置、数据库和知识库文档按周期备份，备份文件与公网目录隔离并限制访问；恢复操作由本人执行并记录。管理账号、云平台账号和域名账号使用高强度独立密码，能够开启多因素验证的平台均开启验证，不向他人共享账号。",
        bold_prefix="5. 备份与权限：",
    )
    add_text(
        document,
        "6. 应急处理：发现异常流量、账号泄露、程序漏洞、违法内容、侵权投诉或个人信息泄露时，立即采取暂停相关接口、下线内容、封禁异常来源、轮换密钥、隔离服务和保全日志等措施；随后排查原因、修复漏洞、恢复验证并形成记录。发生较大网络安全事件时，立即停止网站服务并按要求向腾讯云及有关主管部门报告，配合调查处理。",
        bold_prefix="6. 应急处理：",
    )
    add_text(
        document,
        "7. 投诉与纠错：访客如发现本人资料、引用或生成回答存在错误、侵权或不当内容，可通过网站公布的联系渠道反馈。本人收到反馈后及时核验；确认问题后删除或更正内容、清理缓存和向量索引，并在必要时暂停相关功能。",
        bold_prefix="7. 投诉与纠错：",
    )

    add_heading(document, "五、域名管理")
    add_text(
        document,
        "1. 域名负责人：notebyzyw.cloud 的注册、实名认证、DNS 解析、续费、备案和安全管理均由本人曾有为负责。域名所有者信息与本次个人备案主体保持一致，不将域名出售、出租、出借或授权其他主体用于未备案服务。",
        bold_prefix="1. 域名负责人：",
    )
    add_text(
        document,
        "2. 有效期管理：本人通过域名注册商控制台核对域名有效期并保持实名认证信息准确，开启到期提醒，在到期前不少于 30 日完成续费；同时检查 DNS 解析、HTTPS 证书和备案信息是否仍与实际服务一致。域名具体到期日期以本次提交的域名证书和注册商控制台记录为准。",
        bold_prefix="2. 有效期管理：",
    )
    add_text(
        document,
        "3. 过期或停用处理：若不再使用该域名，将先停止解析和网站服务，妥善处理网站数据，并依法办理备案注销或变更；如发生异常过期，将立即暂停对外服务并联系注册商续费恢复，在确认域名仍由本人控制、DNS 和证书安全后再上线，防止域名被他人接管或用于违法用途。",
        bold_prefix="3. 过期或停用处理：",
    )

    add_heading(document, "六、上线与合规安排")
    add_text(
        document,
        "网站在取得 ICP 备案审核结果并完成接入配置后再正式向公众开放；备案通过后在网站底部按规定展示备案号并链接至备案管理系统。网站正式上线后，将按规定及时办理公安联网备案。若后续新增经营性服务、公众信息发布、新闻、出版、教育、医疗、金融、网络视听等内容，将在获得相应许可或审批并完成备案变更前保持相关功能关闭。"
    )


def add_commitment(document: Document) -> None:
    """保留模板承诺，并填写主办者姓名和日期。"""
    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    add_heading(document, "七、承诺")
    add_text(
        document,
        "本人郑重承诺：本网站是个人网站，本人承诺网站不含有企业、单位等非个人网站的信息。如有违反以上承诺的行为，或发现已备案主体信息有误、网站实际开办内容与备案信息不一致、已备案域名有交易行为、网站内容涉及法律法规禁止的违法违规内容，本人自愿接受接入服务商和通信管理部门依法关闭网站、注销备案并列入相关管理名单等处理。本人保证本方案内容与网站实际建设、运营情况一致，并持续履行网站内容和网络信息安全管理责任。"
    )

    document.add_paragraph()
    signature = document.add_paragraph()
    signature.paragraph_format.left_indent = Cm(8.5)
    signature.paragraph_format.space_before = Pt(30)
    style_run(signature.add_run("网站主办者签名：曾有为"), size=14)
    date = document.add_paragraph()
    date.paragraph_format.left_indent = Cm(8.5)
    date.paragraph_format.space_before = Pt(22)
    style_run(date.add_run("日期：2026年9月14日"), size=14)


def write_guide() -> None:
    """生成备案上传、邮件和系统备注说明。"""
    content = """湖南省个人网站备案提交说明（曾有为）

一、你需要先完成的事项
1. 打开“网站建设方案书-曾有为.docx”，确认“新增服务名称”与腾讯云备案订单完全一致。
2. 如备案订单中的服务名称不是“曾有为的个人技术展示”，请同步修改 Word 和 PDF 中的名称。
3. 核对网站域名为 notebyzyw.cloud，服务器确为本次腾讯云备案订单关联的中国大陆实例。
4. 文档已填写姓名和日期；正式提交前仍建议打印并由曾有为本人在姓名处手写确认、按手印。
5. 将签署后的全部页面按顺序扫描，保证内容清晰、四角完整、无裁切、无反光。

二、腾讯云备案系统上传
将签署后的每一页导出或扫描为图片，按页码顺序上传到“补充材料”位置。不要只上传最后签字页。

三、发送至湖南管局邮箱
收件人：hunan_beian@163.com
邮件主题：接入商（腾讯云计算（北京）有限责任公司广州分公司）+曾有为
附件文件名：曾有为.pdf

邮件正文：
管局审核老师您好：

本人曾有为，现提交 notebyzyw.cloud 新增网站服务备案所需的《网站建设方案书（个人）》。附件为本人签名、按手印并填写日期后的完整扫描 PDF，请查收。

备案主办者：曾有为
网站域名：notebyzyw.cloud
新增服务名称：曾有为的个人技术展示（如备案订单名称不同，请改成订单中的准确名称）
接入商：腾讯云计算（北京）有限责任公司广州分公司
联系电话：【填写备案手机号】
发件邮箱：【填写实际发件邮箱】
发送日期：【填写实际发送日期】

感谢审核。

四、备案审核系统“服务备注”填写内容
网站建设方案书已于【YYYY年MM月DD日】通过邮箱【你的实际发件邮箱】发送至湖南管局邮箱 hunan_beian@163.com，邮件主题为“接入商（腾讯云计算（北京）有限责任公司广州分公司）+曾有为”，请查收。

五、重要说明
- 当前生成的 PDF 是待签字底稿，不能直接代替本人手写签名和手印。
- 正式邮件附件必须使用“签名+手印+日期”后的扫描件，并命名为“曾有为.pdf”。
- 腾讯云官方要求湖南省材料同时完成“备案系统图片上传”和“邮件发送 PDF”两种提交方式。
"""
    GUIDE_TXT.write_text(content, encoding="utf-8")


def main() -> None:
    """构建可编辑方案书和提交说明。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_diagram(DIAGRAM)
    shutil.copy2(REFERENCE, FINAL_DOCX)
    document = Document(FINAL_DOCX)
    clear_document_body(document)
    configure_styles(document)
    add_cover(document)
    add_main_content(document)
    add_commitment(document)
    document.core_properties.title = "网站建设方案书（个人）"
    document.core_properties.subject = "notebyzyw.cloud 新增网站服务备案"
    document.core_properties.author = "曾有为"
    document.save(FINAL_DOCX)
    write_guide()
    print(FINAL_DOCX)
    print(GUIDE_TXT)


if __name__ == "__main__":
    main()
