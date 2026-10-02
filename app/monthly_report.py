"""Aylık bilgilendirme raporu (birimlere gönderilmek üzere).

Kurumun daha önce kullandığı "Yıllık Genel İstatistik" çıktısının biçimini izler:
her ay için proje satırları, Bireysel / Sistemsel / Toplam sütunları, ay toplamı ve genel toplam.
Ek olarak dairesel grafikler içerir.

  Sayfa 1: Seçilen ayın özeti (proje tablosu, oranlar, önceki ayla karşılaştırma, 2 dairesel grafik)
  Sayfa 2: Yıllık genel istatistik (Ocak - seçilen ay, iki sütunlu ay blokları, genel toplam, 2 dairesel grafik)

KVKK: Dosya birimlerle paylaşılacağı için kişisel veri (talep sahibi adı, telefon, açıklama)
İÇERMEZ; yalnızca sayısal istatistikler bulunur. Sayımlar programdan alınır, toplamlar formüldür.
"""
from collections import defaultdict
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.chart import PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.styles import Alignment, Border, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.pagebreak import Break

from .constants import MONTHS_TR, SOURCE_SYSTEM, SOURCE_USER
from .excel_report import BLUE, MUTED, NAVY, ORANGE, _f, _font, _rich, _set, _title
from .extensions import db
from .models import Project, SupportTicket as T

LIGHT = PatternFill("solid", fgColor="DEEBF7")     # başlık bandı
BIREYSEL_FILL = PatternFill("solid", fgColor="BDD7EE")
DARK = PatternFill("solid", fgColor="2F5597")      # Toplam sütunu ve ay toplamı
SECTION = PatternFill("solid", fgColor=NAVY)
LINE = Side(style="thin", color="FFFFFF")
CELL_BORDER = Border(left=LINE, right=LINE, top=LINE, bottom=LINE)
PROJECT_COLORS = ["1BAF7A", "4A3AA7", "EDA100", "E87BA4", "008300", "E34948", "2A78D6", "EB6834"]

BLOCKS = ((1, "A"), (6, "F"))       # sol blok A-D (Ocak-Haziran), sağ blok F-I (Temmuz-Aralık)


def default_period(today=None):
    """Varsayılan: tamamlanmış son ay."""
    today = today or date.today()
    first = today.replace(day=1)
    prev = date.fromordinal(first.toordinal() - 1)
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
# Biçimli tablo parçaları
# --------------------------------------------------------------------------- #

def _header(ws, row, col):
    labels = ("Proje", "Bireysel", "Sistemsel", "Toplam")
    fills = (None, BIREYSEL_FILL, None, DARK)
    for i, (label, fill) in enumerate(zip(labels, fills)):
        c = _set(ws, (row, col + i), label, font=_font(10, True, "FFFFFF" if fill is DARK else NAVY),
                 alignment=Alignment(horizontal="left" if i == 0 else "center"))
        if fill:
            c.fill = fill
        c.border = CELL_BORDER


def _data_row(ws, row, col, name, user, system, bold=False):
    _set(ws, (row, col), name, font=_font(10, bold, NAVY), border=CELL_BORDER)
    b = _set(ws, (row, col + 1), user, font=_font(10, bold), alignment=Alignment(horizontal="center"))
    b.fill, b.border = BIREYSEL_FILL, CELL_BORDER
    _set(ws, (row, col + 2), system, font=_font(10, bold), alignment=Alignment(horizontal="center"), border=CELL_BORDER)
    L = lambda k: ws.cell(row=row, column=col + k).coordinate  # noqa: E731
    _f(ws, (row, col + 3), f"={L(1)}+{L(2)}", font=_font(10, True, "FFFFFF"), fill=DARK,
       alignment=Alignment(horizontal="center"), border=CELL_BORDER)


def _total_row(ws, row, col, label, first, last):
    """Ay toplamı: proje satırlarının toplamı (formül)."""
    _set(ws, (row, col), label, font=_font(10, True, "FFFFFF"), fill=DARK, border=CELL_BORDER)
    for k in (1, 2, 3):
        letter = ws.cell(row=row, column=col + k).column_letter
        formula = f"=SUM({letter}{first}:{letter}{last})" if last >= first else "=0"
        _f(ws, (row, col + k), formula, font=_font(10, True, "FFFFFF"), fill=DARK,
           alignment=Alignment(horizontal="center"), border=CELL_BORDER)


def _pie(ws, anchor, title, cats, values, colors, from_rows=False, width=9.4, height=8.0):
    pie = PieChart()
    pie.add_data(values, titles_from_data=False, from_rows=from_rows)
    pie.set_categories(cats)
    pie.title = _title(title)
    for i, color in enumerate(colors):
        pt = DataPoint(idx=i)
        pt.graphicalProperties.solidFill = color
        pt.graphicalProperties.line.solidFill = "FFFFFF"
        pie.series[0].dPt.append(pt)
    labels = DataLabelList()
    labels.showPercent = True
    for attr in ("showVal", "showSerName", "showCatName", "showLegendKey"):
        setattr(labels, attr, False)
    labels.txPr = _rich(900, True, "FFFFFF")
    pie.series[0].dLbls = labels
    pie.legend.position = "b"
    pie.legend.txPr = _rich(800)
    pie.width, pie.height = width, height
    ws.add_chart(pie, anchor)


def _section(ws, row, text):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=9)
    _set(ws, (row, 1), text, font=_font(11, True, "FFFFFF"), fill=SECTION,
         alignment=Alignment(horizontal="center", vertical="center"))
    ws.row_dimensions[row].height = 20


# --------------------------------------------------------------------------- #
# Rapor
# --------------------------------------------------------------------------- #

def build_monthly_workbook(year, month, org_name):
    data = collect(year, month)
    projects = db.session.execute(db.select(Project).order_by(Project.sort_order, Project.id)).scalars().all()
    month_name = MONTHS_TR[month]

    wb = Workbook()
    wb._named_styles["Normal"].font = _font()
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    ws = wb.active
    ws.title = f"{month_name} {year}"
    ws.sheet_view.showGridLines = False
    for col, width in zip("ABCDEFGHI", (24, 10, 10, 10, 3, 24, 10, 10, 10)):
        ws.column_dimensions[col].width = width

    # Başlık
    ws.merge_cells("A1:I1")
    _set(ws, "A1", f"AYLIK DESTEK İSTATİSTİĞİ — {month_name.upper()} {year}", font=_font(16, True, NAVY),
         fill=LIGHT, alignment=Alignment(horizontal="center", vertical="center"))
    ws.row_dimensions[1].height = 32
    ws.merge_cells("A2:I2")
    _set(ws, "A2", f"{org_name}  ·  Bilgilendirme amaçlıdır  ·  Oluşturma: {datetime.now():%d.%m.%Y}",
         font=_font(9, color=MUTED), alignment=Alignment(horizontal="center"))

    # ---------------- Sayfa 1: seçilen ayın özeti ----------------
    _section(ws, 4, f"{month_name.upper()} {year} ÖZETİ")
    _header(ws, 5, 1)
    month_data = data.get(month, {})
    shown = [p for p in projects if p.active or p.id in month_data]
    first = 6
    for i, p in enumerate(shown):
        d = month_data.get(p.id, {SOURCE_USER: 0, SOURCE_SYSTEM: 0})
        _data_row(ws, first + i, 1, p.name, d[SOURCE_USER], d[SOURCE_SYSTEM])
    last = first + len(shown) - 1
    total_row = last + 1
    _total_row(ws, total_row, 1, f"{month_name} Toplam", first, last)
    rate_row = total_row + 1
    _set(ws, (rate_row, 1), "Oran", font=_font(9, True, MUTED))
    for k, col in ((1, "B"), (2, "C")):
        _f(ws, (rate_row, 1 + k), f"=IF($D${total_row}=0,0,{col}{total_row}/$D${total_row})",
           font=_font(9, True, MUTED), number_format="0.0%", alignment=Alignment(horizontal="center"))

    note_row = rate_row + 1
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=9)
    _set(ws, (note_row, 1), "Bireysel: kullanıcı işlemi kaynaklı · Sistemsel: sistem kaynaklı talepler. "
                            "Arşivlenen kayıtlar dahil değildir. Kaynak: Teknik Destek Kayıt Programı.",
         font=_font(8, color=MUTED), alignment=Alignment(horizontal="left"))

    # Önceki ayla karşılaştırma ve açıklamalar (sağ taraf)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_total = _count_month(prev_year, prev_month)
    notes = [
        ("Önceki ay", f"{MONTHS_TR[prev_month]} {prev_year}: {prev_total} kayıt"),
        ("Değişim", f'=IF({prev_total}=0,"-",($D${total_row}-{prev_total})/{prev_total})'),
        ("Bireysel", "Kullanıcı işlemi kaynaklı talepler"),
        ("Sistemsel", "Sistem kaynaklı talepler"),
    ]
    for i, (label, value) in enumerate(notes):
        r = 5 + i
        _set(ws, (r, 6), label, font=_font(9, True, NAVY))
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=9)
        if value.startswith("="):
            _f(ws, (r, 7), value, font=_font(9, True), number_format="+0.0%;-0.0%;0.0%",
               alignment=Alignment(horizontal="left"))
        else:
            _set(ws, (r, 7), value, font=_font(9, color=MUTED))

    # Dairesel grafikler: kaynak dağılımı ve projelere göre
    chart_row = note_row + 2
    _pie(ws, f"A{chart_row}", f"{month_name} {year} — Bireysel / Sistemsel",
         Reference(ws, min_col=2, max_col=3, min_row=5, max_row=5),
         Reference(ws, min_col=2, max_col=3, min_row=total_row, max_row=total_row),
         (ORANGE, BLUE), from_rows=True)
    _pie(ws, f"F{chart_row}", f"{month_name} {year} — Projelere Göre",
         Reference(ws, min_col=1, min_row=first, max_row=last),
         Reference(ws, min_col=4, min_row=first, max_row=last),
         PROJECT_COLORS[:len(shown)])

    # ---------------- Sayfa 2: yıllık genel istatistik ----------------
    year_row = chart_row + 18
    ws.row_breaks.append(Break(id=year_row - 1))
    _section(ws, year_row, f"YILLIK GENEL İSTATİSTİK — {year} (Ocak – {month_name})")
    for col, _ in BLOCKS[:1 if month <= 6 else 2]:
        _header(ws, year_row + 1, col)

    month_totals = []          # (satır, sütun) ay toplamı hücreleri
    project_rows = []          # (satır, sütun) proje satırları (yıllık proje toplamı için)
    rows_at = {1: year_row + 2, 6: year_row + 2}
    for m in range(1, month + 1):
        col = BLOCKS[0][0] if m <= 6 else BLOCKS[1][0]
        r = rows_at[col]
        ws.merge_cells(start_row=r, start_column=col, end_row=r, end_column=col + 3)
        _set(ws, (r, col), MONTHS_TR[m], font=_font(10, True, NAVY), fill=LIGHT,
             alignment=Alignment(horizontal="center"))
        r += 1
        m_data = data.get(m, {})
        m_projects = [p for p in projects if p.id in m_data]
        start = r
        for p in m_projects:
            d = m_data[p.id]
            _data_row(ws, r, col, p.name, d[SOURCE_USER], d[SOURCE_SYSTEM])
            project_rows.append((r, col))
            r += 1
        if not m_projects:
            _set(ws, (r, col), "Kayıt yok", font=_font(9, color=MUTED))
            r += 1
        _total_row(ws, r, col, f"{MONTHS_TR[m]} Toplam", start, start + len(m_projects) - 1)
        month_totals.append((r, col))
        rows_at[col] = r + 1

    # Genel toplam
    g = max(rows_at.values()) + 1
    _set(ws, (g, 1), "Genel Toplam", font=_font(12, True, "FFFFFF"), fill=SECTION)
    for k in (1, 2, 3):
        refs = "+".join(ws.cell(row=r, column=c + k).coordinate for r, c in month_totals)
        _f(ws, (g, 1 + k), f"={refs}", font=_font(12, True, "FFFFFF"), fill=SECTION,
           alignment=Alignment(horizontal="center"))
    ws.row_dimensions[g].height = 22

    # Yıllık proje toplamları (grafik için; ay bloklarındaki proje satırlarından formülle)
    y = g + 2
    _set(ws, (y, 6), f"{year} Proje Toplamları", font=_font(10, True, NAVY))
    _header(ws, y + 1, 6)
    year_projects = [p for p in projects if any(p.id in data.get(m, {}) for m in range(1, month + 1))]
    left = f"$A${year_row + 2}:$A${rows_at[1]}"
    right = f"$F${year_row + 2}:$F${rows_at[6]}"
    for i, p in enumerate(year_projects):
        r = y + 2 + i
        _set(ws, (r, 6), p.name, font=_font(10, False, NAVY), border=CELL_BORDER)
        for k, (lc, rc) in enumerate((("B", "G"), ("C", "H")), start=1):
            lr = f"${lc}${year_row + 2}:${lc}${rows_at[1]}"
            rr = f"${rc}${year_row + 2}:${rc}${rows_at[6]}"
            cell = _f(ws, (r, 6 + k), f"=SUMIF({left},$F{r},{lr})+SUMIF({right},$F{r},{rr})",
                      font=_font(10), alignment=Alignment(horizontal="center"), border=CELL_BORDER)
            if k == 1:
                cell.fill = BIREYSEL_FILL
        _f(ws, (r, 9), f"=G{r}+H{r}", font=_font(10, True, "FFFFFF"), fill=DARK,
           alignment=Alignment(horizontal="center"), border=CELL_BORDER)
    yp_last = y + 1 + max(len(year_projects), 1)

    pie_row = yp_last + 2
    _pie(ws, f"A{pie_row}", f"{year} — Bireysel / Sistemsel",
         Reference(ws, min_col=2, max_col=3, min_row=year_row + 1, max_row=year_row + 1),
         Reference(ws, min_col=2, max_col=3, min_row=g, max_row=g), (ORANGE, BLUE), from_rows=True,
         width=8.6, height=6.6)
    if year_projects:
        _pie(ws, f"F{pie_row}", f"{year} — Projelere Göre",
             Reference(ws, min_col=6, min_row=y + 2, max_row=yp_last),
             Reference(ws, min_col=9, min_row=y + 2, max_row=yp_last),
             PROJECT_COLORS[:len(year_projects)], width=8.6, height=6.6)

    foot = pie_row + 13
    # Yazdırma: A4 dikey, sayfa genişliğine sığdır
    ws.print_area = f"A1:I{foot}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.5
    ws.print_options.horizontalCentered = True
    ws.oddFooter.left.text = f"{org_name}"
    ws.oddFooter.right.text = "Sayfa &P / &N"
    return wb
