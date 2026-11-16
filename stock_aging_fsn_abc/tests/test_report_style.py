# -*- coding: utf-8 -*-
import io
import zipfile

from odoo.tests.common import TransactionCase, tagged

from ..report.stock_analysis_report import blend, donut_svg, pareto_svg, smooth_path


@tagged('post_install', '-at_install')
class TestReportStyle(TransactionCase):

    def test_blend(self):
        self.assertEqual(blend('#000000', 0.0), '#ffffff')
        self.assertEqual(blend('#000000', 1.0), '#000000')
        self.assertEqual(blend('#34d6b0', 1.0), '#34d6b0')

    def test_smooth_path_passes_through_points(self):
        path = smooth_path([(0.0, 0.0), (10.0, 5.0), (20.0, 2.0)])
        self.assertTrue(path.startswith('M0.0,0.0'))
        self.assertTrue(path.rstrip().endswith('20.0,2.0'))

    def test_donut_cases(self):
        self.assertIn('<path', str(donut_svg([(3, '#111'), (1, '#222')], '4', 'X')))
        self.assertIn('<circle', str(donut_svg([(4, '#111'), (0, '#222')], '4', 'X')))   # single class
        self.assertIn('<circle', str(donut_svg([(0, '#111'), (0, '#222')], '0', 'X')))   # empty

    def test_pareto_many_products(self):
        items = [(100.0 - i, min(100.0, (i + 1) * 100.0 / 60), 'A') for i in range(60)]
        svg = str(pareto_svg(items, 80, 95))
        self.assertEqual(svg.count('<rect'), 60)
        self.assertNotIn('<circle', svg)  # no dots on crowded charts

    def test_render_all_reports_even_without_data(self):
        report = self.env.ref('stock_aging_fsn_abc.action_report_stock_analysis')
        for report_type in ('aging', 'fsn', 'abc', 'loss'):
            wizard = self.env['stock.analysis.wizard'].create({'report_type': report_type})
            html, _fmt = report._render_qweb_html(report.report_name, wizard.ids)
            self.assertIn(b'sa_title', html)

    def test_xlsx_all_reports(self):
        for report_type in ('aging', 'fsn', 'abc', 'loss'):
            wizard = self.env['stock.analysis.wizard'].create({'report_type': report_type, 'output_format': 'xlsx'})
            report = wizard._prepare_report()
            if not report['rows']:
                continue
            archive = zipfile.ZipFile(io.BytesIO(wizard._build_xlsx(report)))
            names = archive.namelist()
            self.assertIn('xl/worksheets/sheet1.xml', names)   # dashboard
            self.assertIn('xl/worksheets/sheet2.xml', names)   # data
