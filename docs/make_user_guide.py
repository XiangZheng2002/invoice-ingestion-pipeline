#!/usr/bin/env python3
"""
生成《使用手册》PDF

用 PyMuPDF 的 Story 把 HTML+CSS 排成 PDF —— PyMuPDF 本来就是项目依赖，
不需要额外装 LaTeX 或 wkhtmltopdf。中文用 sans-serif，MuPDF 会自动
落到内置的 CJK 字体并把子集嵌进 PDF，在任何机器上都能正常显示。

用法：
    python docs/make_user_guide.py

输出：docs/邮件发票识别系统-使用手册.pdf
"""

import os
import sys

for _s in (sys.stdout, sys.stderr):
    if _s is not None and hasattr(_s, 'reconfigure'):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            pass

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(HERE, 'images')
OUTPUT = os.path.join(HERE, '邮件发票识别系统-使用手册.pdf')

PAGE = pymupdf.paper_rect('a4')
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 56, 56, 64

ACCENT = '#4F46E5'
INK = '#111827'
MUTED = '#6B7280'

CSS = f"""
* {{ font-family: sans-serif; color: {INK}; }}

body {{ font-size: 10.5px; line-height: 1.62; }}

/* ---- 封面 ---- */
.cover-title   {{ font-size: 30px; font-weight: bold; margin-top: 150px; }}
.cover-sub     {{ font-size: 13px; color: {MUTED}; margin-top: 10px; line-height: 1.8; }}
.cover-meta    {{ font-size: 10px; color: {MUTED}; margin-top: 40px; }}
.cover-rule    {{ background-color: {ACCENT}; height: 3px; width: 70px; margin-top: 24px; }}

/* ---- 标题 ---- */
h1 {{ font-size: 19px; font-weight: bold; margin-top: 4px; margin-bottom: 4px; }}
h2 {{ font-size: 13.5px; font-weight: bold; margin-top: 18px; margin-bottom: 4px; }}
h3 {{ font-size: 11.5px; font-weight: bold; margin-top: 13px; margin-bottom: 2px; }}
.chapter-no {{ font-size: 10px; color: {ACCENT}; font-weight: bold; margin-bottom: 2px; }}

p  {{ margin-top: 5px; margin-bottom: 5px; }}
ul, ol {{ margin-top: 4px; margin-bottom: 8px; }}
li {{ margin-bottom: 3px; line-height: 1.7; }}

b {{ font-weight: bold; }}
.muted {{ color: {MUTED}; }}
.small {{ font-size: 9.5px; }}
.accent {{ color: {ACCENT}; font-weight: bold; }}

/* ---- 提示框 ---- */
.note, .warn, .tip {{
    padding: 9px 11px; margin-top: 9px; margin-bottom: 9px; font-size: 10px; line-height: 1.7;
}}
.note {{ background-color: #EEF2FF; }}
.warn {{ background-color: #FFFBEB; }}
.tip  {{ background-color: #F3F4F6; }}
.note-title, .warn-title {{ font-weight: bold; }}

/* ---- 表格 ---- */
table {{ width: 100%; margin-top: 8px; margin-bottom: 10px; font-size: 9.5px; }}
th {{ background-color: #F3F4F6; font-weight: bold; text-align: left; padding: 5px 7px; }}
td {{ padding: 4px 7px; line-height: 1.55; }}

/* ---- 图 ---- */
img {{ width: 100%; margin-top: 2px; margin-bottom: 12px; }}
.caption {{ font-size: 9px; color: {MUTED}; margin-top: 10px; margin-bottom: 2px; }}

/* ---- 步骤 ---- */
.step-title {{ font-weight: bold; font-size: 11px; margin-top: 12px; }}

code {{ background-color: #F3F4F6; font-size: 9.5px; }}
.path {{ background-color: #F3F4F6; font-size: 9.5px; padding: 1px 3px; }}

/* 注意：不要用 CSS 的 page-break-before。MuPDF 的 Story 在文档里出现
   多次强制分页时会陷入无限翻页（实测 5 章就翻不完）。改成每个章节
   单独建一个 Story 渲染，天然从新页开始，也更好控制。 */
"""


def cover():
    return """
<div class="cover-title">邮件发票识别系统</div>
<div class="cover-rule"></div>
<div class="cover-sub">
把发票拖进来就能识别，或者让它自动去邮箱里翻。<br/>
电子发票不需要任何配置，识别完直接导出报销用的 CSV。
</div>
<div class="cover-meta">
使用手册 · v1.0<br/>
适用于 macOS 与 Windows 桌面版
</div>
"""


# 目录条目 -> 它对应 sections() 里的下标，页码由第一遍排版算出来
TOC_ENTRIES = [
    ('1', '这个软件能做什么', 2),
    ('2', '安装与首次启动', 3),
    ('3', '最快上手：拖拽识别', 4),
    ('4', '从邮箱批量获取', 6),
    ('5', '百度 OCR（可选）', 9),
    ('6', '导出报销表', 10),
    ('7', '数据存在哪、怎么备份', 11),
    ('8', '常见问题', 12),
    ('A', '附录：支持的邮箱与格式', 13),
]


def toc(page_of_section=None):
    """目录。page_of_section 是"节下标 -> 起始页码"，第一遍排版时传 None"""
    rows = ''
    for num, title, section_index in TOC_ENTRIES:
        page = page_of_section.get(section_index, '') if page_of_section else ''
        rows += (f'<tr><td width="8%" class="accent">{num}</td>'
                 f'<td width="77%">{title}</td>'
                 f'<td width="15%" class="muted">{page}</td></tr>')
    return f'<h1>目录</h1><table>{rows}</table>'


def chapter_1():
    return """
<div class="chapter-no">第 1 章</div>
<h1>这个软件能做什么</h1>

<p>它把发票变成一张可以直接交给财务的表格。你给它发票文件，或者让它去邮箱里翻，
它读出发票号码、开票日期、销售方、金额、税额，存进本地数据库，最后导出 CSV。</p>

<h2>两种用法</h2>
<table>
<tr><th width="22%">方式</th><th width="43%">适合什么时候</th><th width="35%">需要配置吗</th></tr>
<tr><td><b>拖拽识别</b></td><td>发票已经在你电脑上（微信、钉钉下载的，或者截图）</td>
    <td class="accent">不需要，打开就能用</td></tr>
<tr><td><b>邮箱收取</b></td><td>发票都是商家发到邮箱里的，懒得一封封下载</td>
    <td>需要填一次邮箱和授权码</td></tr>
</table>

<h2>为什么电子发票不需要 OCR</h2>

<p>国内的电子发票（PDF 或 OFD 文件）本身就带着文字层，很多还内嵌了一份结构化数据。
软件直接把这些数据读出来，<b>不是靠图像识别猜的</b>。所以：</p>

<ul>
<li>不需要注册百度云账号，不需要申请任何密钥</li>
<li>不消耗任何额度，识别多少张都免费</li>
<li>完全离线，发票内容不会发到任何服务器</li>
<li>准确率比 OCR 高，因为读的是原始数据而不是图片</li>
</ul>

<div class="note">
<span class="note-title">只有这两种情况才需要 OCR：</span>
纸质发票的扫描件、手机拍的发票照片。这类文件里没有文字层，只能靠图像识别。
配置方法见第 5 章，不配也不影响电子发票。
</div>

<h2>你的数据在哪</h2>
<p>全部在你自己电脑上。这个软件不联网上传任何东西——邮箱授权码加密存在本地，
发票文件和识别结果也都在程序旁边的文件夹里。</p>
"""


def chapter_2():
    return """
<div class="chapter-no">第 2 章</div>
<h1>安装与首次启动</h1>

<p>不需要安装 Python 或任何运行环境，下载下来双击就能用。</p>

<h2>2.1 macOS 首次打开</h2>

<p>第一次双击会弹出<b>「无法打开，因为无法验证开发者」</b>。这不是程序有问题，
是因为没有购买 Apple 的开发者证书做签名。绕过方法：</p>

<div class="step-title">在图标上点右键 → 选「打开」→ 弹窗里再点一次「打开」</div>
<p class="small muted">注意必须是右键菜单里的「打开」，直接双击是不行的。之后就不会再提示了。</p>

<p>如果右键也不行，打开「终端」执行这一行（把路径换成实际位置）：</p>
<p><span class="path">xattr -cr /Applications/邮件发票识别系统.app</span></p>

<h2>2.2 Windows 首次打开</h2>

<p>会弹出蓝色的 SmartScreen 提示<b>「Windows 已保护你的电脑」</b>，同样是没做代码签名导致的。</p>

<div class="step-title">点「更多信息」→ 点「仍要运行」</div>

<p>如果杀毒软件报毒，把程序加进白名单。这类打包程序被误报是常见现象。</p>

<h2>2.3 启动之后</h2>

<p>双击后会直接弹出程序窗口，不需要打开浏览器，也不需要记什么网址。
窗口关掉程序就退出了。</p>

<div class="warn">
<span class="warn-title">建议先把程序放到一个固定位置再用。</span>
软件会在<b>程序旁边</b>创建 <span class="path">data</span> 文件夹存放数据。
如果你把程序从「下载」文件夹挪到别处，记得把 <span class="path">data</span> 一起挪过去，
否则之前识别的发票就找不到了。详见第 7 章。
</div>

<h2>2.4 界面长什么样</h2>

<p>顶部五个入口：<b>概览</b>看统计，<b>上传识别</b>拖发票，<b>发票</b>看结果和导出，
<b>邮件</b>从邮箱收，<b>设置</b>填邮箱和密钥。</p>
"""


def chapter_2_image():
    return """
<div class="caption">概览页：已识别的发票数量、价税合计，以及最近识别的几张</div>
<img src="overview.jpg" />
"""


def chapter_3():
    return """
<div class="chapter-no">第 3 章</div>
<h1>最快上手：拖拽识别</h1>

<p>这是最省事的方式，<b>不需要任何配置</b>，打开软件就能用。</p>

<h2>3.1 三步搞定</h2>

<div class="step-title">第一步　点顶部的「上传识别」</div>
<div class="step-title">第二步　把发票文件拖进虚线框</div>
<p>也可以点「选择文件」从电脑里挑，支持一次选多个。</p>
<div class="step-title">第三步　等结果出来，去「发票」页导出 CSV</div>

<div class="caption">上传页。虚线框里可以直接拖文件，也可以拖整个文件夹</div>
<img src="upload-empty.jpg" />

<h2>3.2 可以直接拖一整个文件夹</h2>

<p>如果你的发票散在一个文件夹里（甚至还分了子文件夹），
直接把文件夹拖进去就行，软件会自己往里翻。</p>

<ul>
<li>自动进入所有子文件夹，不用你一层层点开</li>
<li>自动跳过不是发票的文件（Word、Excel、截图说明等）</li>
<li>自动跳过超过 50MB 的文件</li>
<li>同一张发票传过了会标成「重复」，不会重复入账</li>
<li>文件多的时候有进度条，中途可以点「停止」</li>
</ul>

<div class="caption">拖入文件夹后的结果：识别成功 3 张，自动忽略了 2 个非发票文件和 1 个超大文件</div>
<img src="upload-result.jpg" />
"""


def chapter_3b():
    return """
<h2>3.3 结果表怎么看</h2>

<table>
<tr><th width="16%">状态</th><th width="84%">含义</th></tr>
<tr><td><b>成功</b></td><td>识别出来了，已经存进数据库</td></tr>
<tr><td><b>重复</b></td><td>这张发票号码之前已经录过，本次跳过，不会重复计入金额</td></tr>
<tr><td><b>失败</b></td><td>没能识别，右边会写明原因。最常见的是扫描件但没配 OCR</td></tr>
</table>

<p>最右边的「来源」列告诉你这张发票是怎么读出来的：</p>

<table>
<tr><th width="26%">来源</th><th width="74%">说明</th></tr>
<tr><td>发票内嵌数据</td><td>PDF 里带着结构化数据，最准确</td></tr>
<tr><td>PDF文字层</td><td>直接读 PDF 里的文字，很准确</td></tr>
<tr><td>OFD文字内容</td><td>读 OFD 文件里的文字</td></tr>
<tr><td>百度OCR</td><td>图片或扫描件，靠图像识别，建议核对一下金额</td></tr>
</table>

<div class="tip">
前三种都是直接读原始数据，基本不会错。只有显示「百度OCR」的那几张
值得你花两秒钟核对一下发票号码和金额。
</div>

<h2>3.4 支持的文件格式</h2>

<table>
<tr><th width="30%">格式</th><th width="30%">要不要 OCR</th><th width="40%">典型来源</th></tr>
<tr><td>PDF</td><td class="accent">不需要</td><td>商家开的电子发票</td></tr>
<tr><td>OFD</td><td class="accent">不需要</td><td>税局下载的电子发票</td></tr>
<tr><td>JPG / PNG / BMP<br/>WEBP / TIFF</td><td>需要</td><td>拍照、截图、扫描件</td></tr>
</table>

<p class="small muted">单个文件最大 50MB。</p>
"""


def chapter_4():
    return """
<div class="chapter-no">第 4 章</div>
<h1>从邮箱批量获取</h1>

<p>如果发票都是商家发到你邮箱的，可以让软件自己去收，不用一封封下载附件。
这个方式需要先花两分钟配置一次。</p>

<h2>4.1 为什么要「授权码」而不是邮箱密码</h2>

<p>大部分邮箱出于安全考虑，不允许第三方程序用你的登录密码。
你需要在邮箱设置里单独生成一个<b>专门给程序用的密码</b>，
各家叫法不同：QQ 和网易叫「授权码」，Gmail 和 iCloud 叫「应用专用密码」。</p>

<div class="note">
<span class="note-title">这是好事。</span>
授权码只能用来收发邮件，改不了你的账号密码，也登录不了网页版。
不想用了随时可以在邮箱设置里作废掉。
</div>

<h2>4.2 配置步骤</h2>

<div class="step-title">第一步　打开「设置」页，填邮箱地址</div>
<p>填完之后，<b>「服务商」会自动识别</b>，下面也会自动显示这家邮箱该怎么拿授权码。
如果认不出来（比如公司自建邮箱），会让你手动填 IMAP 服务器地址。</p>

<div class="caption">设置页。填入邮箱后自动识别服务商，并列出该邮箱获取授权码的具体步骤</div>
<img src="config.jpg" />
"""


def chapter_4b():
    return """
<div class="step-title">第二步　按页面上的步骤去邮箱里拿授权码，粘贴进来</div>
<p>各家邮箱的入口见下表，具体步骤软件界面上也会显示：</p>

<table>
<tr><th width="20%">邮箱</th><th width="14%">凭证叫法</th><th width="66%">在哪里拿</th></tr>
<tr><td>QQ / Foxmail</td><td>授权码</td>
    <td>网页版 → 设置 → 账户 → POP3/IMAP/SMTP → 开启 IMAP 服务</td></tr>
<tr><td>163 / 126 / yeah</td><td>授权码</td>
    <td>网页版 → 设置 → POP3/SMTP/IMAP → 开启 IMAP 服务</td></tr>
<tr><td>Gmail</td><td>应用专用密码</td>
    <td>账号需先开两步验证 → myaccount.google.com/apppasswords</td></tr>
<tr><td>iCloud</td><td>App 专用密码</td>
    <td>需先开双重认证 → account.apple.com → 登录与安全</td></tr>
<tr><td>新浪 / 阿里云<br/>移动 139</td><td>密码或授权码</td>
    <td>各自网页版设置里开启 IMAP 服务</td></tr>
</table>

<div class="warn">
<span class="warn-title">Outlook / Hotmail 个人账号目前用不了。</span>
微软从 2024 年 9 月起停用了个人账号的 IMAP 密码登录，需要 OAuth 授权，本软件暂不支持。
变通办法：在 Outlook 里设置自动转发，把发票邮件转到 QQ 或 163 邮箱；
或者直接用第 3 章的拖拽识别。
</div>

<div class="step-title">第三步　设置日期权限范围</div>
<p>这里设的是<b>允许收取的最大范围</b>，相当于一道保险，防止误操作把好几年的邮件全拉下来。
实际每次收哪几天，在「邮件」页单独选。</p>

<div class="step-title">第四步　点「测试连接」</div>
<p>连接成功后，软件会把你邮箱里的<b>所有文件夹列出来</b>，可以在「收取文件夹」里选。
一般选默认的 INBOX（收件箱）就行。</p>

<div class="note">
<span class="note-title">Gmail 用户注意：</span>
Gmail 会把邮件「归档」出收件箱，只搜 INBOX 很可能一封发票都找不到。
测试连接后请把「收取文件夹」改成 <span class="path">[Gmail]/All Mail</span>。
</div>

<div class="step-title">第五步　点「保存配置」</div>
"""


def chapter_4c():
    return """
<h2>4.3 收取和识别</h2>

<div class="step-title">第一步　打开「邮件」页，选好起始和终止日期</div>
<p>终止日期留空表示一直到最新。日期范围必须在设置页设定的权限范围内，
超出时软件会提示你是否自动放宽。</p>

<div class="step-title">第二步　点「获取邮件」</div>
<p>软件会把这段时间的邮件抓下来列在下方。邮件多的话会花一点时间。</p>

<div class="step-title">第三步　点「识别发票」</div>
<p>软件会自动挑出像发票的邮件，下载附件并识别：
PDF/OFD 附件直接解析，图片附件走 OCR（需要已配置）。</p>

<div class="step-title">第四步　去「发票」页看结果、导出 CSV</div>

<div class="tip">
识别过的邮件会被标记，再点一次「识别发票」不会重复处理。
同一张发票即使出现在多封邮件里，也只会入账一次。
</div>

<h2>4.4 关于隐私</h2>
<p>邮箱授权码用加密方式存在本地数据库里，不会明文保存，也不会发送到任何地方。
软件只读取邮件，不会发送、删除或修改你的任何邮件。</p>
"""


def chapter_5():
    return """
<div class="chapter-no">第 5 章</div>
<h1>百度 OCR（可选）</h1>

<p><b>如果你的发票都是电子发票，这一章可以整章跳过。</b></p>

<h2>5.1 什么时候才需要</h2>
<p>只有这两种情况：</p>
<ul>
<li>纸质发票的扫描件</li>
<li>手机拍的发票照片</li>
</ul>
<p>这类文件里没有文字，只能靠图像识别，而图像识别需要调用百度的接口。</p>

<h2>5.2 怎么申请</h2>

<div class="step-title">第一步　访问百度智能云 OCR 控制台</div>
<p><span class="path">https://console.bce.baidu.com/ai/#/ai/ocr/overview/index</span></p>

<div class="step-title">第二步　注册并登录，创建一个应用</div>
<p>选「文字识别」类目，应用名随便填。</p>

<div class="step-title">第三步　在应用列表里复制三个值</div>
<p>APP ID、API Key、Secret Key。</p>

<div class="step-title">第四步　填进软件的「设置」页，点「测试 OCR 配置」</div>

<h2>5.3 额度</h2>
<p>百度 OCR 免费额度是每天 500 次调用。一张图片发票算一次，
电子发票不消耗额度。正常报销用量完全够。</p>

<div class="note">
<span class="note-title">每个人用自己的账号。</span>
密钥填在你自己电脑上、加密存在本地，用的是你自己的免费额度，不会和别人共用。
</div>
"""


def chapter_6():
    return """
<div class="chapter-no">第 6 章</div>
<h1>导出报销表</h1>

<p>识别完的发票都在「发票」页。点右上角<b>「导出 CSV」</b>就会下载一个表格文件，
可以直接用 Excel 或 WPS 打开。</p>

<div class="caption">发票页。支持搜索、按任意列排序、分页</div>
<img src="invoice-list.jpg" />

<h2>表格里有什么</h2>
<p>发票号码、发票代码、类型、开票日期、购买方、销售方、
不含税金额、税额、价税合计。</p>

<h2>几个实用操作</h2>
<ul>
<li><b>找某一张</b>：右上角搜索框，输公司名或发票号码都行</li>
<li><b>按金额排序</b>：点「价税合计」列头</li>
<li><b>核对总额</b>：「概览」页顶部直接显示所有发票的价税合计</li>
</ul>

<div class="tip">
导出的是当前数据库里的全部发票。如果只想导某一批，
可以先在「邮件」页清空旧记录再重新识别，或者导出后在 Excel 里筛选。
</div>
"""


def chapter_7():
    return """
<div class="chapter-no">第 7 章</div>
<h1>数据存在哪、怎么备份</h1>

<p>软件会在<b>程序所在目录</b>自动创建这些文件夹（macOS 上是 .app 的同级目录）：</p>

<table>
<tr><th width="34%">位置</th><th width="66%">内容</th></tr>
<tr><td><span class="path">data/invoices.db</span></td><td>所有发票和邮件记录</td></tr>
<tr><td><span class="path">data/encryption.key</span></td><td>加密密钥，用来解开保存的邮箱授权码</td></tr>
<tr><td><span class="path">data/attachments/</span></td><td>邮件附件和你上传过的发票原件</td></tr>
<tr><td><span class="path">data/exports/</span></td><td>导出的 CSV</td></tr>
<tr><td><span class="path">logs/app.log</span></td><td>运行日志，出问题时看这里</td></tr>
</table>

<div class="warn">
<span class="warn-title">换电脑或升级版本时，把整个 data 文件夹一起复制过去。</span><br/>
其中 <span class="path">data/encryption.key</span> 尤其重要：丢了它，
已保存的邮箱授权码和 OCR 密钥就再也解不开了，需要重新填一遍。
发票数据本身没有加密，不受影响。
</div>

<h2>备份建议</h2>
<p>直接把 <span class="path">data</span> 文件夹复制一份到网盘或移动硬盘即可，
没有别的隐藏文件需要处理。</p>

<h2>想清空重来</h2>
<p>在「邮件」页点「清空列表」会删除所有邮件和发票记录。
这个操作不可恢复，会二次确认。</p>
"""


def chapter_8():
    return """
<div class="chapter-no">第 8 章</div>
<h1>常见问题</h1>

<h3>双击没反应，或者窗口一闪而过</h3>
<p>打开程序目录下的 <span class="path">logs/app.log</span>，
最后几行会写明原因。把这个文件发给技术支持最有帮助。</p>

<h3>提示「无法验证开发者」/「Windows 已保护你的电脑」</h3>
<p>正常现象，因为没做代码签名。处理方法见第 2 章。</p>

<h3>界面变成了浏览器窗口</h3>
<p>说明系统缺少内置浏览器组件（常见于较老的 Windows 10）。
功能完全不受影响。想恢复独立窗口的话，装一下微软的 WebView2 运行时。</p>

<h3>邮箱连接失败：「认证失败」</h3>
<ul>
<li>确认填的是<b>授权码</b>而不是邮箱登录密码</li>
<li>确认已经在邮箱设置里<b>开启了 IMAP 服务</b>（这一步最容易漏）</li>
<li>授权码可能已失效——改过邮箱密码、或者关过 IMAP 服务都会导致失效，重新生成一个即可</li>
</ul>

<h3>邮箱能连上，但一封发票都没找到</h3>
<ul>
<li><b>Gmail 用户</b>：把「收取文件夹」改成 <span class="path">[Gmail]/All Mail</span>，
    归档的邮件不在收件箱里</li>
<li>检查日期范围是不是选窄了</li>
<li>确认发票确实是以附件形式发来的（有些商家只发一个下载链接，这种识别不了，
    需要自己下载后用拖拽识别）</li>
</ul>

<h3>识别失败：「PDF没有文字层（可能是扫描件）」</h3>
<p>这个 PDF 其实是一张图片。需要配置百度 OCR（第 5 章），或者找商家要真正的电子发票。</p>

<h3>金额或公司名识别错了</h3>
<p>如果「来源」列显示的是「百度OCR」，说明是图像识别的结果，出错有可能。
显示「PDF文字层」或「发票内嵌数据」却出错的话，
把那个 PDF 文件发给技术支持，可以针对性修正。</p>

<h3>同一张发票被录了两次</h3>
<p>正常情况不会——软件按发票号码去重。如果确实发生了，
说明这两张的发票号码不同，值得核对一下是不是真的是两张不同的发票。</p>

<h3>能同时给好几个人用吗</h3>
<p>这是单机软件，每个人在自己电脑上装一份，各自的数据互不影响。
不是给多人共享一份数据设计的。</p>
"""


def appendix():
    return """
<div class="chapter-no">附录 A</div>
<h1>支持的邮箱与格式</h1>

<h2>支持的邮箱</h2>
<table>
<tr><th width="26%">邮箱</th><th width="34%">域名</th><th width="40%">说明</th></tr>
<tr><td>QQ / Foxmail</td><td>qq.com, foxmail.com</td><td>用授权码</td></tr>
<tr><td>网易 163 / 126 / yeah</td><td>163.com, 126.com, yeah.net</td><td>用授权码</td></tr>
<tr><td>Gmail</td><td>gmail.com</td><td>用应用专用密码，注意改文件夹</td></tr>
<tr><td>iCloud</td><td>icloud.com, me.com</td><td>用 App 专用密码</td></tr>
<tr><td>新浪</td><td>sina.com, sina.cn</td><td>密码或授权码</td></tr>
<tr><td>阿里云</td><td>aliyun.com</td><td>密码</td></tr>
<tr><td>中国移动 139</td><td>139.com</td><td>用授权码</td></tr>
<tr><td>Outlook / Hotmail</td><td>outlook.com 等</td><td>个人账号暂不可用</td></tr>
<tr><td><b>其他邮箱</b></td><td>任意</td><td>手动填 IMAP 服务器地址即可</td></tr>
</table>

<h2>支持的发票格式</h2>
<table>
<tr><th width="24%">格式</th><th width="24%">识别方式</th><th width="52%">准确度</th></tr>
<tr><td>PDF（电子发票）</td><td>直接读取</td><td>很高，读的是原始数据</td></tr>
<tr><td>OFD（电子发票）</td><td>直接读取</td><td>很高</td></tr>
<tr><td>JPG / PNG / BMP<br/>WEBP / TIFF</td><td>百度 OCR</td><td>取决于图片清晰度，建议核对</td></tr>
</table>

<h2>可识别的发票类型</h2>
<table>
<tr><td width="50%">电子发票（普通发票）·「数电票」</td><td width="50%">增值税电子普通发票（旧版）</td></tr>
<tr><td>电子发票（增值税专用发票）</td><td>增值税专用发票</td></tr>
<tr><td>电子发票（铁路电子客票）</td><td>航空运输电子客票行程单</td></tr>
</table>

<div class="tip">
遇到识别不了的发票类型，把文件发给技术支持，通常加一条规则就能支持。
</div>
"""


def sections(page_of_section=None):
    """每个元素渲染成独立的 Story，因此都会从新的一页开始"""
    return [
        cover(),
        toc(page_of_section),
        chapter_1(),
        chapter_2() + chapter_2_image(),
        chapter_3(),
        chapter_3b(),
        chapter_4(),
        chapter_4b(),
        chapter_4c(),
        chapter_5(),
        chapter_6(),
        chapter_7(),
        chapter_8(),
        appendix(),
    ]


def add_footers(path):
    """加页脚页码。Story 不管页眉页脚，生成完再逐页盖上去"""
    doc = pymupdf.open(path)
    total = doc.page_count
    font = pymupdf.Font('china-ss')

    for i, page in enumerate(doc):
        if i == 0:          # 封面不加
            continue
        y = PAGE.height - 34
        page.draw_line(pymupdf.Point(MARGIN_X, y - 12),
                       pymupdf.Point(PAGE.width - MARGIN_X, y - 12),
                       color=(0.90, 0.91, 0.92), width=0.6)

        writer = pymupdf.TextWriter(page.rect)
        writer.append(pymupdf.Point(MARGIN_X, y), '邮件发票识别系统 · 使用手册',
                      font=font, fontsize=8)
        label = f'{i + 1} / {total}'
        width = font.text_length(label, fontsize=8)
        writer.append(pymupdf.Point(PAGE.width - MARGIN_X - width, y), label,
                      font=font, fontsize=8)
        writer.write_text(page, color=(0.55, 0.58, 0.62))

    doc.saveIncr()
    doc.close()
    return total


def add_outline(path, starts):
    """
    生成 PDF 书签

    直接用排版算出的章节起始页，不要去搜标题文本 ——
    目录页上列着所有章节名，按文本搜会全部命中第 2 页。
    """
    doc = pymupdf.open(path)
    toc_entries = [[1, '目录', starts.get(1, 2)]]
    for _, title, section_index in TOC_ENTRIES:
        page = starts.get(section_index)
        if page:
            toc_entries.append([1, title, page])
    doc.set_toc(toc_entries)
    doc.set_metadata({
        'title': '邮件发票识别系统 · 使用手册',
        'author': '邮件发票识别系统',
        'subject': '安装、拖拽识别、邮箱收取与导出报销表的完整说明',
    })
    doc.saveIncr()
    doc.close()
    return len(toc_entries)


def compress(path):
    """
    子集化字体并清理

    每个 Story 都会把整份 CJK 字体嵌进去，14 个章节就是 14 份，
    不处理的话 PDF 会有 7MB 以上。子集化后只留用到的字形，约 290KB。
    """
    doc = pymupdf.open(path)
    doc.subset_fonts()
    doc.save(path + '.tmp', garbage=4, deflate=True, clean=True)
    doc.close()
    os.replace(path + '.tmp', path)


def render(page_of_section, path):
    """把所有章节排进一个 PDF，返回 {节下标: 起始页码}（页码从 1 开始）"""
    archive = pymupdf.Archive(IMAGES)
    writer = pymupdf.DocumentWriter(path)
    where = pymupdf.Rect(MARGIN_X, MARGIN_TOP,
                         PAGE.width - MARGIN_X, PAGE.height - MARGIN_BOTTOM)

    starts = {}
    pages = 0
    for index, html in enumerate(sections(page_of_section)):
        starts[index] = pages + 1
        story = pymupdf.Story(html=html, user_css=CSS, archive=archive)
        more, guard = 1, 0
        while more:
            device = writer.begin_page(PAGE)
            more, _ = story.place(where)
            story.draw(device)
            writer.end_page()
            pages += 1
            guard += 1
            if guard > 12:      # 单章排不完说明内容有问题，别把整本卡死
                print(f'警告: 第 {index} 节超过 12 页，已截断')
                break
    writer.close()
    return starts


def audit(path):
    """找出内容过少的页面（通常是某章多溢出一两行造成的）"""
    doc = pymupdf.open(path)
    sparse = []
    for i, page in enumerate(doc):
        blocks = page.get_text('blocks')
        # 排除页脚那一行
        body = [b for b in blocks if b[3] < PAGE.height - 50]
        used = sum(b[3] - b[1] for b in body)
        ratio = used / (PAGE.height - MARGIN_TOP - MARGIN_BOTTOM)
        has_img = len(page.get_images()) > 0
        if ratio < 0.30 and not has_img and i > 0:
            first = (body[0][4].strip().split('\n')[0][:24] if body else '(空)')
            sparse.append((i + 1, round(ratio * 100), first))
    doc.close()
    return sparse


def main():
    if not os.path.isdir(IMAGES):
        print(f'找不到配图目录: {IMAGES}')
        return 1

    # 第一遍：先排一次，量出每章落在第几页
    tmp = OUTPUT + '.pass1'
    starts = render(None, tmp)

    # 第二遍：把真实页码填进目录再排一次
    render(starts, OUTPUT)
    if os.path.exists(tmp):
        os.remove(tmp)

    total = add_footers(OUTPUT)
    marks = add_outline(OUTPUT, starts)
    compress(OUTPUT)

    sparse = audit(OUTPUT)
    if sparse:
        print('  内容偏少的页面（可考虑调整章节长度）:')
        for pno, pct, first in sparse:
            print(f'    第 {pno} 页 仅占 {pct}%  首行: {first}')

    size = os.path.getsize(OUTPUT) / 1024
    print(f'已生成: {OUTPUT}')
    print(f'  {total} 页 · {size:.0f} KB · {marks} 个书签')
    print('  目录页码:', {t: starts.get(i) for _, t, i in TOC_ENTRIES})
    return 0


if __name__ == '__main__':
    sys.exit(main())
