# -*- coding: utf-8 -*-
from odoo import api, models


class ReportStockAnalysis(models.AbstractModel):
    _name = 'report.stock_aging_fsn_abc.report_stock_analysis'
    _description = 'Stock Analysis PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['stock.analysis.wizard'].browse(docids)
        wizard.ensure_one()
        return {
            'doc_ids': docids,
            'doc_model': 'stock.analysis.wizard',
            'docs': wizard,
            'o': wizard,
            'report': wizard._prepare_report(),
            'fmt': wizard._fmt,
        }
