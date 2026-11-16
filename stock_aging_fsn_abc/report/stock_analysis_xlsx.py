# -*- coding: utf-8 -*-
"""Excel (XLSX) rendering of the stock analysis reports.

Two sheets, the same colours as the PDF:

* Dashboard: title, KPI cards, a small legend table and native Excel charts
  (stock value by age, FSN donut, ABC Pareto, top losses).
* Data sheet: purple header, heat-map cells for the aging buckets, class
  pills for FSN / ABC, data bars, auto filter and SUBTOTAL totals that follow
  the filters.

Only XlsxWriter 3.0.x features are used (the version pinned by Odoo 17).
"""
import io
import math

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from odoo import _, models

from .stock_analysis_report import (ABC_COLORS, CLASS_COLORS, DONUT_COLORS, EPS, INK, MUTED,
                                    PURPLE, SCALE, blend)

ZEBRA, LINE, TINT, CARD = '#fcf9fb', '#f0e8ee', '#f4ecf1', '#f8f3f7'
NUMFMT = {'float': '#,##0.00', 'money': '#,##0.00', 'int': '#,##0', 'pct': '0.0"%"'}
DASH_COLS = 12


class _Formats(object):
    """Format factory with a cache (XlsxWriter formats are workbook objects)."""

    def __init__(self, workbook):
        self.workbook = workbook
        self.cache = {}

    def __call__(self, **props):
        key = tuple(sorted(props.items()))
        if key not in self.cache:
            base = {'font_name': 'Calibri', 'font_size': 10, 'font_color': INK, 'valign': 'vcenter'}
            base.update(props)
            self.cache[key] = self.workbook.add_format(base)
        return self.cache[key]


def _qty_format(value, dash_zero=False):
    whole = abs(value - round(value)) < 1e-6
    base = '#,##0' if whole else '#,##0.00'
    return base + ';-' + base + ';"–"' if dash_zero else base


class ReportStockAnalysisXlsx(models.AbstractModel):
    _inherit = 'report.stock_aging_fsn_abc.report_stock_analysis'

    # ------------------------------------------------------------------
    def _build_xlsx(self, wizard, report):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        formats = _Formats(workbook)
        dashboard = workbook.add_worksheet(_('Dashboard')[:31])
        data = workbook.add_worksheet(report['sheet_name'][:31])
        kpis = self._build_pdf(wizard, report)['kpis']
        meta = self._xlsx_data_sheet(wizard, report, data, formats)
        self._xlsx_dashboard(wizard, report, workbook, dashboard, meta, kpis, formats)
        workbook.close()
        return output.getvalue()

    # ------------------------------------------------------------------
    # data sheet
    # ------------------------------------------------------------------
    def _xlsx_layout(self, wizard):
        """(n_text columns for aging, quantity columns, frozen columns, muted column)"""
        report_type = wizard.report_type
        if report_type == 'aging':
            n_text = 3 if wizard.lot_level else 2
            return n_text, set(range(n_text, n_text + 6)), n_text, 0
        if report_type == 'fsn':
            return None, {3, 4}, 2, 0
        if report_type == 'abc':
            return None, {7}, 3, 1
        return None, {3, 4, 5, 6}, 2, 0

    def _class_code(self, wizard, label):
        if wizard.report_type == 'abc':
            return label if label in ABC_COLORS else 'C'
        names = {_('Fast'): 'F', _('Slow'): 'S', _('Non-moving'): 'N'}
        return names.get(label, 'N')

    def _xlsx_data_sheet(self, wizard, report, ws, F):
        report_type = wizard.report_type
        columns, rows, totals = report['columns'], report['rows'], report['totals']
        ncols = len(columns)
        n_text, qty_cols, freeze, muted_col = self._xlsx_layout(wizard)
        header_row = 3
        first, last = header_row + 1, header_row + len(rows)

        bucket_of = {}
        if report_type == 'aging':
            for i in range(5):
                bucket_of[n_text + 1 + i] = i      # quantity bucket
                bucket_of[n_text + 7 + i] = i      # value bucket

        ws.hide_gridlines(2)
        ws.write(0, 0, report['title'], F(bold=True, font_size=16))
        ws.set_row(0, 26)
        ws.write(1, 0, report['subtitle'], F(font_color=MUTED, font_size=9))

        # header ----------------------------------------------------------
        ws.set_row(header_row, 34)
        for c, col in enumerate(columns):
            if c in bucket_of:
                fmt = F(bold=True, bg_color=SCALE[bucket_of[c]], font_color=INK, text_wrap=True, align='center')
            else:
                is_class = report_type in ('fsn', 'abc') and c == 9
                fmt = F(bold=True, bg_color=PURPLE, font_color='#ffffff', text_wrap=True,
                        align='center' if is_class else ('left' if col['type'] == 'text' else 'right'))
            ws.write(header_row, c, col['label'], fmt)

        # body ------------------------------------------------------------
        widths = [max(12, min(len(col['label']) * 0.9 + 2, 24)) for col in columns]
        for r, row in enumerate(rows):
            zebra = ZEBRA if r % 2 else None
            top = max(row[n_text + 1:n_text + 6]) if report_type == 'aging' else None
            for c, value in enumerate(row):
                kind = columns[c]['type']
                props = {'bottom': 1, 'bottom_color': LINE}
                if zebra:
                    props['bg_color'] = zebra
                if c == muted_col and kind == 'text':
                    props.update(font_color=MUTED, font_size=9)
                if report_type in ('fsn', 'abc') and c == 9:                 # class pill
                    bg, fg = CLASS_COLORS[self._class_code(wizard, value)]
                    props.update(bg_color=bg, font_color=fg, bold=True, align='center')
                if c in bucket_of:                                          # heat map
                    qty = row[n_text + 1 + bucket_of[c]]
                    if qty > EPS:
                        props['bg_color'] = blend(SCALE[bucket_of[c]], 0.14 + 0.50 * qty / (top or 1.0))
                        if c < n_text + 6:
                            props['bold'] = True
                if value is None or value is False or value == '':
                    ws.write_blank(first + r, c, None, F(**props))
                    continue
                if kind == 'text':
                    ws.write_string(first + r, c, str(value), F(**props))
                    widths[c] = max(widths[c], min(len(str(value)) + 2, 38))
                    continue
                if c in qty_cols:
                    props['num_format'] = _qty_format(value, dash_zero=c in bucket_of)
                elif c in bucket_of:
                    props['num_format'] = '#,##0.00;-#,##0.00;"–"'
                else:
                    props['num_format'] = NUMFMT.get(kind, 'General')
                ws.write_number(first + r, c, value, F(**props))

        # totals ----------------------------------------------------------
        total_row = last + 1
        if totals and rows:
            for c in range(ncols):
                value = totals[c]
                props = {'bold': True, 'bg_color': TINT, 'top': 2, 'top_color': PURPLE}
                if value is None:
                    ws.write_blank(total_row, c, None, F(**props))
                elif isinstance(value, str):
                    ws.write_string(total_row, c, value, F(**props))
                else:
                    if c in qty_cols:
                        props['num_format'] = _qty_format(value, dash_zero=c in bucket_of)
                    else:
                        props['num_format'] = NUMFMT.get(columns[c]['type'], 'General')
                    letter = xl_col_to_name(c)
                    ws.write_formula(total_row, c, '=SUBTOTAL(109,%s%d:%s%d)' % (letter, first + 1, letter, last + 1),
                                     F(**props), value)

        # cosmetics -------------------------------------------------------
        for c, width in enumerate(widths):
            ws.set_column(c, c, width)
        ws.freeze_panes(first, freeze)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(header_row)
        ws.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
        if rows:
            ws.autofilter(header_row, 0, last, ncols - 1)
        if report_type == 'abc' and rows:
            ws.conditional_format(first, 4, last, 4, {'type': 'data_bar', 'bar_color': '#9be7d3', 'bar_solid': True})
        if report_type == 'loss' and rows:
            ws.conditional_format(first, 7, last, 7, {'type': 'data_bar', 'bar_color': '#ff9f7a', 'bar_solid': True})
        return {'name': ws.get_name(), 'first': first, 'last': last, 'n_text': n_text}

    # ------------------------------------------------------------------
    # dashboard
    # ------------------------------------------------------------------
    def _xlsx_dashboard(self, wizard, report, workbook, ws, meta, kpis, F):
        ws.hide_gridlines(2)
        ws.set_column(0, DASH_COLS - 1, 14)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 1)
        ws.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.5)
        last_col = DASH_COLS - 1
        ws.merge_range(0, 0, 0, last_col, report['title'], F(bold=True, font_size=20))
        ws.set_row(0, 36)
        ws.merge_range(1, 0, 1, last_col, report['subtitle'], F(font_color=MUTED, font_size=9, text_wrap=True, valign='top'))
        ws.set_row(1, 30)
        ws.merge_range(2, 0, 2, last_col, '', F(bg_color=PURPLE))
        ws.set_row(2, 5)
        ws.set_row(3, 10)

        # KPI cards -------------------------------------------------------
        count = max(len(kpis), 1)
        span = 4 if count <= 3 else (3 if count == 4 else 2)
        ws.set_row(4, 28)
        ws.set_row(5, 32)
        for i, kpi in enumerate(kpis):
            c0 = i * span
            c1 = min(c0 + span - 1, last_col)
            if c0 > last_col:
                break
            side = {'left': 5, 'left_color': '#ffffff', 'right': 5, 'right_color': '#ffffff'}
            ws.merge_range(4, c0, 4, c1, kpi['label'].upper(),
                           F(bg_color=CARD, font_size=8, bold=True, font_color=MUTED, text_wrap=True,
                             valign='bottom', indent=1, **side))
            ws.merge_range(5, c0, 5, c1, kpi['value'],
                           F(bg_color=CARD, font_size=14, bold=True, font_color=kpi['color'], valign='top',
                             indent=1, **side))

        getattr(self, '_xlsx_dash_%s' % wizard.report_type)(wizard, report, workbook, ws, meta, F)

    # --- shared chart helpers -------------------------------------------
    @staticmethod
    def _style_chart(chart, title, width, height):
        chart.set_title({'name': title, 'name_font': {'name': 'Calibri', 'size': 12, 'bold': True, 'color': INK}})
        chart.set_size({'width': width, 'height': height})
        chart.set_chartarea({'border': {'color': '#eadfe7'}, 'fill': {'color': '#ffffff'}})
        chart.set_plotarea({'fill': {'none': True}})

    @staticmethod
    def _axes(chart, num_format='#,##0'):
        chart.set_y_axis({'num_format': num_format, 'line': {'none': True},
                          'major_gridlines': {'visible': True, 'line': {'color': '#efe5ec'}},
                          'num_font': {'color': MUTED, 'size': 9}})
        chart.set_x_axis({'line': {'color': '#cdbfc9'}, 'num_font': {'color': MUTED, 'size': 9}})

    def _table_header(self, ws, row, labels, F):
        for c, label in enumerate(labels):
            ws.write(row, c, label, F(bold=True, bg_color=PURPLE, font_color='#ffffff', align='left' if c == 0 else 'right',
                                      text_wrap=True))
        ws.set_row(row, 24)

    # --- aging ------------------------------------------------------------
    def _xlsx_dash_aging(self, wizard, report, workbook, ws, meta, F):
        n_text = meta['n_text']
        totals = report['totals']
        qtys = totals[n_text + 1:n_text + 6]
        values = totals[n_text + 7:n_text + 12]
        total_value = totals[n_text + 6] or 0.0
        labels = [_('%s d') % lb for lb in wizard._bucket_labels()]
        top = 7
        self._table_header(ws, top, [_('Age bucket'), _('Qty'), _('Value'), _('% of value')], F)
        for i, label in enumerate(labels):
            r = top + 1 + i
            ws.write(r, 0, label, F(bold=True, bg_color=SCALE[i], font_color=INK, bottom=1, bottom_color='#ffffff'))
            ws.write_number(r, 1, qtys[i], F(num_format=_qty_format(qtys[i]), bottom=1, bottom_color=LINE))
            ws.write_number(r, 2, values[i], F(num_format='#,##0.00', bottom=1, bottom_color=LINE))
            ws.write_number(r, 3, (values[i] / total_value * 100.0) if total_value else 0.0,
                            F(num_format='0.0"%"', bottom=1, bottom_color=LINE))
        r = top + 6
        tot = {'bold': True, 'bg_color': TINT, 'top': 2, 'top_color': PURPLE}
        ws.write(r, 0, _('Total'), F(**tot))
        ws.write_number(r, 1, sum(qtys), F(num_format=_qty_format(sum(qtys)), **tot))
        ws.write_number(r, 2, sum(values), F(num_format='#,##0.00', **tot))
        ws.write_number(r, 3, 100.0 if total_value else 0.0, F(num_format='0.0"%"', **tot))

        sheet = ws.get_name()
        for title, col, anchor in ((_('Stock value by age'), 2, (15, 0)), (_('Quantity by age'), 1, (15, 6))):
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name': title,
                'categories': [sheet, top + 1, 0, top + 5, 0],
                'values': [sheet, top + 1, col, top + 5, col],
                'points': [{'fill': {'color': SCALE[i]}} for i in range(5)],
                'gap': 45,
                'data_labels': {'value': True, 'num_format': '#,##0', 'font': {'size': 9, 'color': INK}},
            })
            self._style_chart(chart, title, 590, 300)
            self._axes(chart)
            chart.set_legend({'none': True})
            ws.insert_chart(anchor[0], anchor[1], chart, {'x_offset': 4})

    # --- FSN --------------------------------------------------------------
    def _xlsx_dash_fsn(self, wizard, report, workbook, ws, meta, F):
        names = [('F', _('Fast')), ('S', _('Slow')), ('N', _('Non-moving'))]
        counts = dict.fromkeys('FSN', 0)
        values = dict.fromkeys('FSN', 0.0)
        for row in report['rows']:
            code = self._class_code(wizard, row[9])
            counts[code] += 1
            values[code] += row[8]
        top = 7
        self._table_header(ws, top, [_('Class'), _('Products'), _('Stock value')], F)
        for i, (code, label) in enumerate(names):
            r = top + 1 + i
            bg, fg = CLASS_COLORS[code]
            ws.write(r, 0, label, F(bold=True, bg_color=bg, font_color=fg, bottom=1, bottom_color='#ffffff'))
            ws.write_number(r, 1, counts[code], F(num_format='#,##0', bottom=1, bottom_color=LINE))
            ws.write_number(r, 2, values[code], F(num_format='#,##0.00', bottom=1, bottom_color=LINE))
        sheet = ws.get_name()
        colors = [DONUT_COLORS[c] for c, _label in names]

        donut = workbook.add_chart({'type': 'doughnut'})
        donut.add_series({
            'name': _('Products by class'),
            'categories': [sheet, top + 1, 0, top + 3, 0],
            'values': [sheet, top + 1, 1, top + 3, 1],
            'points': [{'fill': {'color': c}} for c in colors],
            'data_labels': {'value': True, 'font': {'bold': True, 'color': '#ffffff', 'size': 11}},
        })
        donut.set_hole_size(55)
        self._style_chart(donut, _('Products by class'), 480, 320)
        donut.set_legend({'position': 'right', 'font': {'color': INK, 'size': 10}})
        ws.insert_chart(12, 0, donut, {'x_offset': 4})

        columns = workbook.add_chart({'type': 'column'})
        columns.add_series({
            'name': _('Stock value by class'),
            'categories': [sheet, top + 1, 0, top + 3, 0],
            'values': [sheet, top + 1, 2, top + 3, 2],
            'points': [{'fill': {'color': c}} for c in colors],
            'gap': 60,
            'data_labels': {'value': True, 'num_format': '#,##0', 'font': {'size': 9, 'color': INK}},
        })
        self._style_chart(columns, _('Stock value by class'), 590, 320)
        self._axes(columns)
        columns.set_legend({'none': True})
        ws.insert_chart(12, 5, columns, {'x_offset': 30})

    # --- ABC --------------------------------------------------------------
    def _xlsx_dash_abc(self, wizard, report, workbook, ws, meta, F):
        rows = report['rows']
        if not any(row[4] > 0 for row in rows):
            return
        sheet, first, last = meta['name'], meta['first'], meta['last']
        columns = workbook.add_chart({'type': 'column'})
        columns.add_series({
            'name': [sheet, 3, 4],
            'categories': [sheet, first, 1, last, 1],
            'values': [sheet, first, 4, last, 4],
            'fill': {'color': ABC_COLORS['A']},
            'points': [{'fill': {'color': ABC_COLORS[self._class_code(wizard, row[9])]}} for row in rows],
            'gap': 35,
        })
        line = workbook.add_chart({'type': 'line'})
        marker = ({'type': 'circle', 'size': 6, 'fill': {'color': '#ffffff'}, 'border': {'color': PURPLE, 'width': 1.75}}
                  if len(rows) <= 30 else {'type': 'none'})
        line.add_series({
            'name': [sheet, 3, 6],
            'categories': [sheet, first, 1, last, 1],
            'values': [sheet, first, 6, last, 6],
            'y2_axis': True,
            'line': {'color': PURPLE, 'width': 2.5},
            'marker': marker,
        })
        columns.combine(line)
        self._style_chart(columns, _('Revenue and cumulative share'), 1180, 380)
        self._axes(columns)
        columns.set_x_axis({'line': {'color': '#cdbfc9'}, 'num_font': {'color': MUTED, 'size': 9, 'rotation': -45},
                            'interval_unit': max(1, int(math.ceil(len(rows) / 40.0)))})
        line.set_y2_axis({'min': 0, 'max': 100, 'major_unit': 20, 'num_format': '0"%"',
                          'major_gridlines': {'visible': False}, 'num_font': {'color': MUTED, 'size': 9}})
        columns.set_legend({'position': 'bottom', 'font': {'color': INK, 'size': 10}})
        ws.insert_chart(7, 0, columns, {'x_offset': 4})

    # --- loss -------------------------------------------------------------
    def _xlsx_dash_loss(self, wizard, report, workbook, ws, meta, F):
        sheet, first = meta['name'], meta['first']
        count = min(len(report['rows']), 10)
        if not count:
            return
        chart = workbook.add_chart({'type': 'bar'})
        chart.add_series({
            'name': [sheet, 3, 7],
            'categories': [sheet, first, 1, first + count - 1, 1],
            'values': [sheet, first, 7, first + count - 1, 7],
            'fill': {'color': '#ff8a5c'},
            'gap': 50,
            'data_labels': {'value': True, 'num_format': '#,##0.00', 'font': {'size': 9, 'color': INK}},
        })
        self._style_chart(chart, _('Top losses by value'), 760, 340)
        chart.set_x_axis({'num_format': '#,##0', 'line': {'none': True},
                          'major_gridlines': {'visible': True, 'line': {'color': '#efe5ec'}},
                          'num_font': {'color': MUTED, 'size': 9}})
        chart.set_y_axis({'reverse': True, 'line': {'color': '#cdbfc9'}, 'num_font': {'color': INK, 'size': 9}})
        chart.set_legend({'none': True})
        ws.insert_chart(7, 0, chart, {'x_offset': 4})
