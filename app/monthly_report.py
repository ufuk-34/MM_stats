"""Aylık bilgilendirme raporu (birimlere gönderilmek üzere).

Sade, kurumsal tasarım: beyaz zemin, ince çizgiler, büyük rakamlar, iki vurgu rengi
(Bireysel = mercan, Sistemsel = petrol) ve halka grafikler. Tek çalışma sayfası, iki A4 baskı sayfası:

  Sayfa 1 - Aylık özet: özet kutuları, projelere göre tablo (pay çubuklu), iki halka grafik
  Sayfa 2 - Yıllık genel istatistik: ay x proje matrisi (Bireysel / Sistemsel / Toplam),
            genel toplam, aylık eğilim grafiği ve yıllık proje dağılımı

KVKK: Dosya birimlerle paylaşılacağı için kişisel veri (talep sahibi adı, telefon, açıklama)
İÇERMEZ; yalnızca sayısal istatistikler bulunur. Sayımlar programdan alınır, toplamlar formüldür.
"""
from collections import defaultdict
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.legend import Legend
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.pagebreak import Break

from .constants import MONTHS_TR, SOURCE_SYSTEM, SOURCE_USER
from .excel_report import _f, _font, _rich, _set, _title
from .extensions import db
from .models import Project, SupportTicket as T

# Tasarım değerleri
INK = "1F2937"          # ana metin
SUB = "6B7280"          # ikincil metin
HAIR = "E5E7EB"         # ince çizgi
ZEBRA = "F8FAFC"        # satır şeridi
TOTAL_BG = "F1F5F9"     # toplam satırı / toplam sütunları
BIREYSEL = "D9622B"     # mercan  (renk körlüğü testinden geçti)
SISTEMSEL = "00929C"    # petrol
PROJECT_COLORS = ["4A3AA7", "C9851A", "C2477A", "2A78D6", "3F8F3A"]
ZERO_DASH = '0;-0;"–"'

COLS = 13               # sayfa 13 eşit sütunlu bir ızgaraya oturur (A-M)
COL_W = 8.1
FIRST_COL_W = 12.5      # ay adları ve "Genel Toplam" için
DATA_COL = 15           # grafik yardımcı verisi: O-P sütunları (yazdırma alanı dışında)
hair = Side(style="thin", color=HAIR)
ink_thin = Side(style="thin", color=INK)
ink_line = Side(style="medium", color=INK)


def default_period(today=None):
    """Varsayılan: tamamlanmış son ay."""
    today = today or date.today()
    prev = date.fromordinal(today.replace(day=1).toordinal() - 1)
    return prev.year, prev.month


def _month_bounds(year, month):
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.min.time())


def collect(year, month):
    """{ay: {proje_id: {"user": n, "system": n}}} — arşivlenmiş kayıtlar hariç."""
    start, _ = _month_bounds(year, 1)
    _, end = _month_bounds(year, month)
    month_col = db.func.strftime("%m", T.created_at)
    rows = db.session.execute(
        db.select(month_col, T.project_id, T.source, db.func.count(T.id))
        .where(T.archived.is_(False), T.created_at >= start, T.created_at < end)
        .group_by(month_col, T.project_id, T.source)
    ).all()
    data = defaultdict(lambda: defaultdict(lambda: {SOURCE_USER: 0, SOURCE_SYSTEM: 0}))
    for m, pid, source, n in rows:
        data[int(m)][pid][source] = n
    return data


def _count_month(year, month):
    start, end = _month_bounds(year, month)
    return db.session.execute(
        db.select(db.func.count(T.id)).where(T.archived.is_(False), T.created_at >= start, T.created_at < end)
    ).scalar() or 0


# --------------------------------------------------------------------------- #
# Tasarım yardımcıları
# --------------------------------------------------------------------------- #

def L(col):
    return get_column_letter(col)


def _merge(ws, row, c1, c2, value, formula=False, **style):
    if c2 > c1:
        ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
    return (_f if formula else _set)(ws, (row, c1), value, **style)


def _line(ws, row, c1, c2, top=None, bottom=None, fill=None):
    """Satır aralığına üst/alt çizgi ve zemin uygular (birleştirilmiş hücreler dahil)."""
    for c in range(c1, c2 + 1):
        cell = ws.cell(row=row, column=c)
        cell.border = Border(top=top, bottom=bottom)
        if fill:
            cell.fill = PatternFill("solid", fgColor=fill)


def _page_header(ws, row, kicker, title, subtitle):
    """Sayfa başlığı: küçük üst etiket, büyük başlık, alt bilgi ve koyu çizgi."""
    _merge(ws, row, 1, COLS, kicker, font=_font(9, True, SUB))
    _merge(ws, row + 1, 1, COLS, title, font=_font(24, True, INK), alignment=Alignment(vertical="center"))
    ws.row_dimensions[row + 1].height = 36
    _merge(ws, row + 2, 1, COLS, subtitle, font=_font(9, color=SUB), alignment=Alignment(vertical="top"))
    ws.row_dimensions[row + 2].height = 18
    _line(ws, row + 3, 1, COLS, top=ink_line)
    ws.row_dimensions[row + 3].height = 8
    return row + 5


def _section_title(ws, row, text, note=""):
    _merge(ws, row, 1, 8, text, font=_font(12, True, INK))
    if note:
        _merge(ws, row, 9, COLS, note, font=_font(8, color=SUB), alignment=Alignment(horizontal="right"))
    _line(ws, row, 1, COLS, bottom=hair)
    ws.row_dimensions[row].height = 20
    return row + 2


def _tile(ws, row, c1, c2, label, value, sub="", color=INK, value_format="0", sub_formula=False, sub_format=None):
    """Özet kutusu: üstte renkli kalın şerit, etiket, büyük değer, alt açıklama."""
    _merge(ws, row, c1, c2, label.upper(), font=_font(8, True, SUB), alignment=Alignment(indent=1, vertical="bottom"))
    _merge(ws, row + 1, c1, c2, value, formula=str(value).startswith("="), font=_font(22, True, color),
           number_format=value_format, alignment=Alignment(indent=1, vertical="center", horizontal="left"))
    _merge(ws, row + 2, c1, c2, sub, formula=sub_formula, font=_font(9, color=SUB),
           number_format=sub_format or "General", alignment=Alignment(indent=1, horizontal="left", vertical="top"))
    top = Side(style="thick", color=color)
    for r in range(row, row + 3):
        for c in range(c1, c2 + 1):
            ws.cell(row=r, column=c).border = Border(
                top=top if r == row else None, bottom=hair if r == row + 2 else None,
                left=hair if c == c1 else None, right=hair if c == c2 else None)
    ws.row_dimensions[row].height = 20
    ws.row_dimensions[row + 1].height = 32
    ws.row_dimensions[row + 2].height = 18


def _doughnut(ws, anchor, title, cats, values, colors, width=9.4, height=7.6):
    ch = DoughnutChart(holeSize=58)
    ch.add_data(values, titles_from_data=False)
    ch.set_categories(cats)
    ch.title = _title(title)
    ch.style = 10
    for i, color in enumerate(colors):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = color
        pt.graphicalProperties.line.solidFill = "FFFFFF"
        pt.graphicalProperties.line.width = 19050
        ch.series[0].dPt.append(pt)
    labels = DataLabelList()
    labels.showPercent = True
    for attr in ("showVal", "showSerName", "showCatName", "showLegendKey"):
        setattr(labels, attr, False)
    labels.txPr = _rich(900, True, "FFFFFF")
    ch.series[0].dLbls = labels
    ch.legend = Legend(legendPos="r")
    ch.legend.txPr = _rich(900, False, INK)
    ch.width, ch.height = width, height
    ws.add_chart(ch, anchor)


def _chart_data(ws, row, rows):
    """Grafik yardımcı verisini yazdırma alanı dışına (O-P sütunları) yazar; ilk satırın numarasını döndürür."""
    for i, (label, value) in enumerate(rows):
        _set(ws, (row + i, DATA_COL), label, font=_font(8, color=SUB))
        cell = (_f if isinstance(value, str) else _set)(ws, (row + i, DATA_COL + 1), value, font=_font(8, color=SUB))
        cell.number_format = "0"
    return row


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #

def build_monthly_workbook(year, month, org_name):
    data = collect(year, month)
    projects = db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars().all()
    month_name = MONTHS_TR[month]

    wb = Workbook()
    wb._named_styles["Normal"].font = _font(10, color=INK)
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    ws = wb.active
    ws.title = f"{month_name} {year}"
    ws.sheet_view.showGridLines = False
    for c in range(1, COLS + 1):
        ws.column_dimensions[L(c)].width = FIRST_COL_W if c == 1 else COL_W
    ws.column_dimensions[L(DATA_COL)].width = 24
    _set(ws, (1, DATA_COL), "Grafik verisi (yazdırılmaz)", font=_font(8, True, SUB))

    # ================= SAYFA 1: AYLIK ÖZET =================
    row = _page_header(ws, 1, "AYLIK DESTEK İSTATİSTİĞİ", f"{month_name} {year}",
                       f"{org_name}   ·   Bilgilendirme amaçlıdır   ·   Oluşturma: {datetime.now():%d.%m.%Y}")

    month_data = data.get(month, {})
    shown = [p for p in projects if p.active or p.id in month_data]
    # Konumlar önceden hesaplanır; özet kutuları tablodaki toplam satırına bağlanır
    tiles_row = row
    table_title_row = tiles_row + 4
    head = table_title_row + 2
    first = head + 1
    last = first + len(shown) - 1
    total_row = last + 1
    tot = lambda col: f"${col}${total_row}"   # noqa: E731

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_total = _count_month(prev_year, prev_month)
    _tile(ws, tiles_row, 1, 3, "Toplam talep", f"={tot('I')}", f"{len(shown)} proje", INK)
    _tile(ws, tiles_row, 4, 6, "Bireysel", f"={tot('E')}",
          f'=IF({tot("I")}=0,"",{tot("E")}/{tot("I")})', BIREYSEL, sub_formula=True, sub_format='0.0%" pay"')
    _tile(ws, tiles_row, 7, 9, "Sistemsel", f"={tot('G')}",
          f'=IF({tot("I")}=0,"",{tot("G")}/{tot("I")})', SISTEMSEL, sub_formula=True, sub_format='0.0%" pay"')
    _tile(ws, tiles_row, 10, 13, "Önceki aya göre",
          f'=IF({prev_total}=0,"–",({tot("I")}-{prev_total})/{prev_total})',
          f"{MONTHS_TR[prev_month]} {prev_year}: {prev_total} talep", INK, value_format="+0.0%;-0.0%;0.0%")

    _section_title(ws, table_title_row, "Projelere Göre Dağılım", "Pay: projenin ay içindeki payı")
    for c1, c2, label in ((1, 4, "PROJE"), (5, 6, "BİREYSEL"), (7, 8, "SİSTEMSEL"), (9, 10, "TOPLAM"), (11, 13, "PAY")):
        _merge(ws, head, c1, c2, label, font=_font(8, True, SUB),
               alignment=Alignment(horizontal="left" if c1 == 1 else "center", indent=1 if c1 == 1 else 0))
    _line(ws, head, 1, COLS, bottom=ink_thin)

    for i, p in enumerate(shown):
        r = first + i
        d = month_data.get(p.id, {SOURCE_USER: 0, SOURCE_SYSTEM: 0})
        _line(ws, r, 1, COLS, bottom=hair, fill=ZEBRA if i % 2 else None)
        _merge(ws, r, 1, 4, p.name, font=_font(10, False, INK), alignment=Alignment(indent=1, vertical="center"))
        _merge(ws, r, 5, 6, d[SOURCE_USER], font=_font(10, color=BIREYSEL), number_format=ZERO_DASH,
               alignment=Alignment(horizontal="center", vertical="center"))
        _merge(ws, r, 7, 8, d[SOURCE_SYSTEM], font=_font(10, color=SISTEMSEL), number_format=ZERO_DASH,
               alignment=Alignment(horizontal="center", vertical="center"))
        _merge(ws, r, 9, 10, f"=E{r}+G{r}", formula=True, font=_font(10, True, INK), number_format=ZERO_DASH,
               alignment=Alignment(horizontal="center", vertical="center"))
        _merge(ws, r, 11, 13, f"=IF({tot('I')}=0,0,I{r}/{tot('I')})", formula=True, font=_font(9, color=SUB),
               number_format="0.0%", alignment=Alignment(horizontal="right", indent=1, vertical="center"))
        ws.row_dimensions[r].height = 21
    if shown:
        ws.conditional_formatting.add(
            f"K{first}:K{last}",
            DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="A9B8CC", showValue=True))

    _line(ws, total_row, 1, COLS, top=ink_thin, fill=TOTAL_BG)
    _merge(ws, total_row, 1, 4, f"{month_name} Toplam", font=_font(10, True, INK),
           alignment=Alignment(indent=1, vertical="center"))
    for c1, c2, letter, color in ((5, 6, "E", BIREYSEL), (7, 8, "G", SISTEMSEL), (9, 10, "I", INK)):
        formula = f"=SUM({letter}{first}:{letter}{last})" if shown else "=0"
        _merge(ws, total_row, c1, c2, formula, formula=True, font=_font(11, True, color),
               alignment=Alignment(horizontal="center", vertical="center"))
    _merge(ws, total_row, 11, 13, f"=IF({tot('I')}=0,0,1)", formula=True, font=_font(9, True, SUB),
           number_format="0%", alignment=Alignment(horizontal="right", indent=1, vertical="center"))
    ws.row_dimensions[total_row].height = 24

    note = total_row + 2
    _merge(ws, note, 1, COLS, "Bireysel: kullanıcı işlemi kaynaklı talepler   ·   Sistemsel: sistem kaynaklı talepler   ·   "
                              "Arşivlenen kayıtlar dahil değildir.", font=_font(8, color=SUB))

    charts = note + 2
    _section_title(ws, charts, "Grafikler")
    src = _chart_data(ws, 3, [("Bireysel", f"={tot('E')}"), ("Sistemsel", f"={tot('G')}")])
    _doughnut(ws, f"A{charts + 2}", "Bireysel / Sistemsel",
              Reference(ws, min_col=DATA_COL, min_row=src, max_row=src + 1),
              Reference(ws, min_col=DATA_COL + 1, min_row=src, max_row=src + 1), (BIREYSEL, SISTEMSEL))
    if shown:
        _doughnut(ws, f"H{charts + 2}", "Projelere Göre",
                  Reference(ws, min_col=1, min_row=first, max_row=last),
                  Reference(ws, min_col=9, min_row=first, max_row=last), PROJECT_COLORS[:len(shown)])
    page1_end = charts + 18

    # ================= SAYFA 2: YILLIK GENEL İSTATİSTİK =================
    ws.row_breaks.append(Break(id=page1_end))
    row = _page_header(ws, page1_end + 1, "YILLIK GENEL İSTATİSTİK", f"{year}",
                       f"Ocak – {month_name} {year}   ·   Aylara ve projelere göre Bireysel / Sistemsel talepler")

    year_projects = [p for p in projects if any(p.id in data.get(m, {}) for m in range(1, month + 1))]
    # Projeler 3'erli gruplar halinde gösterilir; her matrisin son grubu "Toplam"
    groups = [year_projects[i:i + 3] for i in range(0, len(year_projects), 3)] or [[]]
    for gi, group in enumerate(groups):
        if gi:
            row += 1
        head1, head2 = row, row + 1
        blocks = [(p.name, p) for p in group] + [("TOPLAM", None)]
        for bi, (label, p) in enumerate(blocks):
            c = 2 + bi * 3
            _merge(ws, head1, c, c + 2, label, font=_font(9, True, INK if p is None else SUB),
                   alignment=Alignment(horizontal="center"))
            _line(ws, head1, c, c + 2, bottom=hair)
            for k, (sub, sub_color) in enumerate((("Bireysel", BIREYSEL), ("Sistemsel", SISTEMSEL), ("Toplam", INK))):
                _set(ws, (head2, c + k), sub, font=_font(7, True, sub_color), alignment=Alignment(horizontal="center"))
        _set(ws, (head2, 1), "AY", font=_font(8, True, SUB), alignment=Alignment(indent=1))
        _line(ws, head2, 1, COLS, bottom=ink_thin)

        m_first = head2 + 1
        m_last = m_first + month - 1
        for m in range(1, month + 1):
            r = m_first + m - 1
            _line(ws, r, 1, COLS, bottom=hair, fill=ZEBRA if m % 2 == 0 else None)
            _set(ws, (r, 1), MONTHS_TR[m], font=_font(10, m == month, INK), alignment=Alignment(indent=1))
            m_data = data.get(m, {})
            for bi, (_, p) in enumerate(blocks):
                c = 2 + bi * 3
                if p is not None:
                    d = m_data.get(p.id, {SOURCE_USER: 0, SOURCE_SYSTEM: 0})
                    user, system, bold = d[SOURCE_USER], d[SOURCE_SYSTEM], False
                else:
                    # Toplam: o ayın tüm projeleri (diğer matrislerdekiler dahil)
                    user = sum(v[SOURCE_USER] for v in m_data.values())
                    system = sum(v[SOURCE_SYSTEM] for v in m_data.values())
                    bold = True
                    for k in range(3):
                        ws.cell(row=r, column=c + k).fill = PatternFill("solid", fgColor=TOTAL_BG)
                _set(ws, (r, c), user, font=_font(10, bold, BIREYSEL), number_format=ZERO_DASH,
                     alignment=Alignment(horizontal="center"))
                _set(ws, (r, c + 1), system, font=_font(10, bold, SISTEMSEL), number_format=ZERO_DASH,
                     alignment=Alignment(horizontal="center"))
                _f(ws, (r, c + 2), f"={L(c)}{r}+{L(c + 1)}{r}", font=_font(10, True, INK), number_format=ZERO_DASH,
                   alignment=Alignment(horizontal="center"))
            ws.row_dimensions[r].height = 19

        g = m_last + 1
        _line(ws, g, 1, COLS, top=ink_line, fill=TOTAL_BG)
        _set(ws, (g, 1), "Genel Toplam", font=_font(10, True, INK), alignment=Alignment(indent=1, vertical="center"))
        for bi in range(len(blocks)):
            c = 2 + bi * 3
            for k, color in enumerate((BIREYSEL, SISTEMSEL, INK)):
                _f(ws, (g, c + k), f"=SUM({L(c + k)}{m_first}:{L(c + k)}{m_last})", font=_font(11, True, color),
                   number_format=ZERO_DASH, alignment=Alignment(horizontal="center", vertical="center"))
        ws.row_dimensions[g].height = 24
        tc = 2 + (len(blocks) - 1) * 3         # bu matristeki "Toplam" bloğunun ilk sütunu
        row = g + 2

    # Yıllık özet cümlesi
    total, user, system = f"{L(tc + 2)}{g}", f"{L(tc)}{g}", f"{L(tc + 1)}{g}"
    _merge(ws, row, 1, COLS,
           f'="Yıl toplamı "&{total}&" talep   ·   Aylık ortalama "&ROUND({total}/{month},0)'
           f'&"   ·   Bireysel %"&ROUND(IF({total}=0,0,{user}/{total})*100,0)'
           f'&"   ·   Sistemsel %"&ROUND(IF({total}=0,0,{system}/{total})*100,0)',
           formula=True, font=_font(10, True, INK))

    # Grafikler: aylık eğilim (yığılmış sütun) ve yıllık proje dağılımı
    charts = row + 2
    _section_title(ws, charts, "Grafikler")
    trend = BarChart()
    trend.type, trend.grouping, trend.overlap, trend.gapWidth = "col", "stacked", 100, 55
    trend.add_data(Reference(ws, min_col=tc, max_col=tc + 1, min_row=head2, max_row=m_last), titles_from_data=True)
    trend.set_categories(Reference(ws, min_col=1, min_row=m_first, max_row=m_last))
    trend.title = _title("Aylara Göre Talepler")
    trend.style = 10
    for s, color in zip(trend.series, (BIREYSEL, SISTEMSEL)):
        s.graphicalProperties.solidFill = color
        s.graphicalProperties.line.solidFill = "FFFFFF"
    trend.x_axis.delete = trend.y_axis.delete = False
    trend.y_axis.majorGridlines = None
    trend.y_axis.numFmt = "0"
    trend.x_axis.txPr = _rich(800, False, SUB)
    trend.y_axis.txPr = _rich(800, False, SUB)
    trend.legend = Legend(legendPos="t")
    trend.legend.txPr = _rich(800, False, INK)
    trend.width, trend.height = 13.2, 7.6
    ws.add_chart(trend, f"A{charts + 2}")

    if year_projects:
        rows = []
        for p in year_projects:
            rows.append((p.name, sum(v.get(p.id, {}).get(SOURCE_USER, 0) + v.get(p.id, {}).get(SOURCE_SYSTEM, 0)
                                     for m, v in data.items() if m <= month)))
        src = _chart_data(ws, 7, rows)
        _doughnut(ws, f"I{charts + 2}", "Projelere Göre (yıl)",
                  Reference(ws, min_col=DATA_COL, min_row=src, max_row=src + len(rows) - 1),
                  Reference(ws, min_col=DATA_COL + 1, min_row=src, max_row=src + len(rows) - 1),
                  PROJECT_COLORS[:len(rows)], width=8.2, height=7.6)

    end = charts + 18
    _merge(ws, end, 1, COLS, "Kaynak: Teknik Destek Kayıt Programı   ·   Bireysel: kullanıcı işlemi kaynaklı   ·   "
                             "Sistemsel: sistem kaynaklı   ·   Arşivlenen kayıtlar dahil değildir.",
           font=_font(8, color=SUB))

    # Yazdırma: A4 dikey, sayfa genişliğine sığdır (O-P yardımcı sütunları basılmaz)
    ws.print_area = f"A1:{L(COLS)}{end}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.55
    ws.page_margins.top = ws.page_margins.bottom = 0.6
    ws.print_options.horizontalCentered = True
    ws.oddFooter.left.text = org_name
    ws.oddFooter.left.size = 8
    ws.oddFooter.right.text = "Sayfa &P / &N"
    ws.oddFooter.right.size = 8
    return wb
