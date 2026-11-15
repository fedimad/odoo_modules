# -*- coding: utf-8 -*-
"""PDF rendering of the stock analysis reports.

The wizard produces a generic table description (columns, rows, totals,
summary). This model turns it into a *presentation* structure used by the QWeb
template: heat-map cells for the aging buckets, class pills for FSN / ABC,
value bars for the losses, KPI cards and small inline SVG charts.

Only features understood by wkhtmltopdf (old WebKit) are used: tables, inline
blocks, solid colours and inline SVG. No flexbox, no CSS grid.
"""
import math

from markupsafe import Markup, escape

from odoo import _, api, models

SCALE = ['#34d6b0', '#8fe36b', '#ffc94d', '#ff9650', '#ff5d73']  # fresh -> old
CLASS_COLORS = {                       # label background, label text
    'F': ('#d1fae5', '#047857'), 'S': ('#fef3c7', '#b45309'), 'N': ('#fee2e2', '#b91c1c'),
    'A': ('#d1fae5', '#047857'), 'B': ('#fef3c7', '#b45309'), 'C': ('#ece4ea', '#6b5a66'),
}
DONUT_COLORS = {'F': '#34d6b0', 'S': '#ffc94d', 'N': '#ff5d73'}
ABC_COLORS = {'A': '#34d6b0', 'B': '#ffc94d', 'C': '#c9b8c2'}
INK, MUTED, PURPLE = '#2a1626', '#8a7684', '#714B67'
EPS = 1e-9


def blend(hex_color, alpha):
    """Colour `hex_color` at opacity `alpha` over a white background, as solid hex."""
    h = hex_color.lstrip('#')
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02x%02x%02x' % tuple(int(round(255 + (c - 255) * alpha)) for c in rgb)


def smooth_path(points):
    """Catmull-Rom spline through `points`, as an SVG cubic Bezier path."""
    path = 'M%.1f,%.1f' % points[0]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        path += ' C%.1f,%.1f %.1f,%.1f %.1f,%.1f' % (c1 + c2 + p2)
    return path


def donut_svg(parts, center_value, center_label, size=130):
    """parts: [(count, color)]. Drawn with arc paths (no dash tricks)."""
    cx = cy = size / 2.0
    radius, width = size * 0.39, size * 0.17
    total = float(sum(c for c, _col in parts))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (size, size, size, size)]
    visible = [(c, col) for c, col in parts if c > 0]
    if total <= 0:
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#ece4ea" stroke-width="%.1f"/>' % (cx, cy, radius, width))
    elif len(visible) == 1:
        out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" stroke-width="%.1f"/>' % (cx, cy, radius, visible[0][1], width))
    else:
        angle, gap = 0.0, 0.035
        for count, color in visible:
            sweep = count / total * 2 * math.pi
            a0, a1 = angle + gap / 2, angle + sweep - gap / 2
            x0, y0 = cx + radius * math.sin(a0), cy - radius * math.cos(a0)
            x1, y1 = cx + radius * math.sin(a1), cy - radius * math.cos(a1)
            out.append('<path d="M%.2f,%.2f A%.2f,%.2f 0 %d 1 %.2f,%.2f" fill="none" stroke="%s" stroke-width="%.1f"/>'
                       % (x0, y0, radius, radius, 1 if (a1 - a0) > math.pi else 0, x1, y1, color, width))
            angle += sweep
    out.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="%d" font-weight="bold" fill="%s" font-family="sans-serif">%s</text>'
               % (cx, cy + 2, size * 0.2, INK, escape(center_value)))
    out.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="%d" font-weight="bold" fill="%s" font-family="sans-serif">%s</text>'
               % (cx, cy + size * 0.14, size * 0.075, MUTED, escape(center_label)))
    out.append('</svg>')
    return Markup(''.join(out))


PARETO_W, PARETO_H = 960, 215


def pareto_svg(items, a_pct, ab_pct, width=PARETO_W, height=PARETO_H):
    """items: [(revenue, cumulative_pct, class_code)], already sorted."""
    left, base, bar_zone, line_zone = 38, height - 12, 105, height - 40
    n = len(items)
    slot = (width - left - 10) / float(n)
    bar_w = max(2.0, min(54.0, slot * 0.7))
    top = max(r for r, _c, _k in items) or 1.0
    # no width/height: the SVG fills a wrapper box that keeps the width/height ratio
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
           'style="position:absolute;left:0;top:0;width:100%%;height:100%%;">' % (width, height)]
    for pct, color in ((a_pct, '#34d6b0'), (ab_pct, '#e0a21a')):
        y = base - pct / 100.0 * line_zone
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="5,4"/>' % (left, width - 8, y, y, color))
        out.append('<text x="2" y="%.1f" font-size="10" font-weight="bold" fill="%s" font-family="sans-serif">%s %%</text>' % (y + 3.5, color, ('%g' % pct)))
    points = []
    for i, (revenue, cum, code) in enumerate(items):
        x = left + i * slot + (slot - bar_w) / 2.0
        h = max(revenue / top * bar_zone, 1.5) if revenue > 0 else 1.5
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"/>'
                   % (x, base - h, bar_w, h, min(7.0, bar_w / 4), ABC_COLORS[code]))
        points.append((x + bar_w / 2.0, base - cum / 100.0 * line_zone))
    if len(points) > 1:
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (smooth_path(points), PURPLE))
    if n <= 30:
        for px, py in points:
            out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#ffffff" stroke="%s" stroke-width="2.4"/>' % (px, py, PURPLE))
    out.append('</svg>')
    return Markup(''.join(out))


class ReportStockAnalysis(models.AbstractModel):
    _name = 'report.stock_aging_fsn_abc.report_stock_analysis'
    _description = 'Stock Analysis PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['stock.analysis.wizard'].browse(docids)
        wizard.ensure_one()
        report = wizard._prepare_report()
        return {
            'doc_ids': docids,
            'doc_model': 'stock.analysis.wizard',
            'docs': wizard,
            'o': wizard,
            'report': report,
            'fmt': wizard._fmt,
            'pdf': self._build_pdf(wizard, report),
        }

    # ------------------------------------------------------------------
    # presentation model
    # ------------------------------------------------------------------
    @api.model
    def _build_pdf(self, wizard, report):
        pdf = {
            'title': report['title'],
            'subtitle': report['subtitle'],
            'chip': str(wizard.as_of_date),
            'columns': [], 'rows': [], 'total': [], 'legend_heat': [], 'legend': [],
            'donut': False, 'pareto': False, 'pareto_ratio': '22%', 'rule': False, 'note': False,
            'kpis': [{'label': label, 'value': value, 'color': INK} for label, value in report['summary']],
        }
        if not report['rows']:
            return pdf
        getattr(self, '_pdf_%s' % wizard.report_type)(wizard, report, pdf)
        return pdf

    @staticmethod
    def _qty(value):
        """Quantity without useless decimals: 236 rather than 236.00."""
        if value is None:
            return ''
        if abs(value - round(value)) < 1e-6:
            return '{:,.0f}'.format(value)
        return '{:,.2f}'.format(value)

    @staticmethod
    def _cell(text, align='r', **kw):
        cell = {'t': text, 'align': align}
        cell.update(kw)
        return cell

    @staticmethod
    def _plain_columns(report, center=()):
        columns, kinds = [], []
        for i, col in enumerate(report['columns']):
            align = 'c' if i in center else ('l' if col['type'] == 'text' else 'r')
            columns.append({'label': col['label'], 'align': align})
            kinds.append(col['type'])
        return columns, kinds

    def _plain_row(self, wizard, row, kinds, columns, muted=(), qty=()):
        cells = []
        for i, value in enumerate(row):
            style = 'color:%s;font-size:9px;' % MUTED if i in muted else ''
            text = self._qty(value) if i in qty else wizard._fmt(value, kinds[i])
            cells.append(self._cell(text, columns[i]['align'], style=style))
        return cells

    def _total_cells(self, wizard, totals, kinds, columns, qty=()):
        cells = []
        for i, value in enumerate(totals):
            if value is None:
                text = ''
            elif i in qty:
                text = self._qty(value)
            else:
                text = wizard._fmt(value, kinds[i])
            cells.append(self._cell(text, columns[i]['align']))
        return cells

    # --- aging -----------------------------------------------------------
    def _pdf_aging(self, wizard, report, pdf):
        n_text = 3 if wizard.lot_level else 2
        labels = wizard._bucket_labels()
        pdf['columns'] = ([{'label': c['label'], 'align': 'l'} for c in report['columns'][:n_text]]
                          + [{'label': _('Qty'), 'align': 'r'}]
                          + [{'label': _('%s d') % lb, 'align': 'r'} for lb in labels]
                          + [{'label': _('Value'), 'align': 'r'}])
        pdf['legend_heat'] = [{'color': SCALE[i], 'label': _('%s d') % lb} for i, lb in enumerate(labels)]
        pdf['note'] = _('Each age cell shows the quantity (top) and its value (bottom).')

        def split(row):
            return (row[n_text], row[n_text + 1:n_text + 6],
                    row[n_text + 6], row[n_text + 7:n_text + 12])

        for row in report['rows']:
            qty, qtys, total_value, values = split(row)
            top = max(qtys) or 1.0
            cells = [self._cell(str(row[0] or ''), 'l', style='color:%s;font-size:9px;' % MUTED)]
            cells += [self._cell(str(v or ''), 'l') for v in row[1:n_text]]
            cells.append(self._cell(self._qty(qty), 'r', style='font-weight:bold;'))
            for i, (q, v) in enumerate(zip(qtys, values)):
                if q > EPS:
                    alpha = 0.14 + 0.50 * q / top
                    cells.append(self._cell(
                        self._qty(q), 'r', sub=wizard._fmt(v, 'money'),
                        style='background-color:%s;font-weight:bold;' % blend(SCALE[i], alpha)))
                else:
                    cells.append(self._cell('–', 'r', style='color:#cdbfc9;'))
            cells.append(self._cell(wizard._fmt(total_value, 'money'), 'r'))
            pdf['rows'].append(cells)

        qty, qtys, total_value, values = split(report['totals'])
        total = [self._cell(report['totals'][0], 'l')] + [self._cell('', 'l') for _i in range(1, n_text)]
        total.append(self._cell(self._qty(qty), 'r'))
        total += [self._cell(self._qty(q), 'r', sub=wizard._fmt(v, 'money'))
                  for q, v in zip(qtys, values)]
        total.append(self._cell(wizard._fmt(total_value, 'money'), 'r'))
        pdf['total'] = total
        if len(pdf['kpis']) > 2:
            pdf['kpis'][2]['color'] = '#e0405a'

    # --- FSN -------------------------------------------------------------
    def _pdf_fsn(self, wizard, report, pdf):
        names = {'F': _('Fast'), 'S': _('Slow'), 'N': _('Non-moving')}
        label_to_code = {label: code for code, label in names.items()}
        columns, kinds = self._plain_columns(report, center=(9,))
        pdf['columns'] = columns
        counts = {'F': 0, 'S': 0, 'N': 0}
        for row in report['rows']:
            code = label_to_code.get(row[9], 'N')
            counts[code] += 1
            cells = self._plain_row(wizard, row[:9], kinds, columns, muted=(0,), qty=(3, 4))
            cells.append(self._cell('', 'c', pill=(row[9],) + CLASS_COLORS[code]))
            pdf['rows'].append(cells)
        pdf['total'] = self._total_cells(wizard, report['totals'], kinds, columns, qty=(3, 4))
        pdf['legend'] = [{'label': names[c], 'count': counts[c], 'color': DONUT_COLORS[c]} for c in 'FSN']
        # KPI cards rebuilt here so that every word goes through the translation
        values = {'F': 0.0, 'S': 0.0, 'N': 0.0}
        for row in report['rows']:
            values[label_to_code.get(row[9], 'N')] += row[8]
        pdf['kpis'] = [{'label': _('%s products') % names[c], 'color': INK,
                        'value': _('%(n)d (stock value %(value)s)') % {'n': counts[c], 'value': wizard._fmt(values[c], 'money')}}
                       for c in 'FSN']
        pdf['donut'] = donut_svg([(counts[c], DONUT_COLORS[c]) for c in 'FSN'],
                                 str(sum(counts.values())), _('Products').upper())
        pdf['rule'] = _('Turnover = quantity sold in the period / quantity on hand. '
                        'No sales: Non-moving. Turnover at or above %(ratio)s: Fast. '
                        'Otherwise: Slow.') % {'ratio': '%g' % wizard.fsn_fast_ratio}

    # --- ABC -------------------------------------------------------------
    def _pdf_abc(self, wizard, report, pdf):
        columns, kinds = self._plain_columns(report, center=(9,))
        pdf['columns'] = columns
        items = []
        for row in report['rows']:
            code = row[9] if row[9] in ABC_COLORS else 'C'
            cells = self._plain_row(wizard, row[:9], kinds, columns, muted=(1,), qty=(7,))
            cells.append(self._cell('', 'c', pill=(code,) + CLASS_COLORS[code]))
            pdf['rows'].append(cells)
            items.append((row[4], row[6], code))
        pdf['total'] = self._total_cells(wizard, report['totals'], kinds, columns, qty=(7,))
        if any(item[0] > 0 for item in items):
            pdf['pareto'] = pareto_svg(items, wizard.abc_a_pct, wizard.abc_a_pct + wizard.abc_b_pct)
            pdf['pareto_ratio'] = '%.2f%%' % (PARETO_H * 100.0 / PARETO_W)

    # --- loss ------------------------------------------------------------
    def _pdf_loss(self, wizard, report, pdf):
        columns, kinds = self._plain_columns(report)
        pdf['columns'] = columns
        top = max([r[7] for r in report['rows']] + [0.0]) or 1.0
        for row in report['rows']:
            cells = self._plain_row(wizard, row[:7], kinds, columns, muted=(0,), qty=(3, 4, 5, 6))
            cells.append(self._cell(wizard._fmt(row[7], 'money'), 'r',
                                    bar=int(round(max(row[7], 0.0) / top * 90)),
                                    style='font-weight:bold;'))
            pdf['rows'].append(cells)
        pdf['total'] = self._total_cells(wizard, report['totals'], kinds, columns, qty=(3, 4, 5, 6))
        if pdf['kpis']:
            pdf['kpis'][0]['color'] = '#e0405a'
