# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################
from odoo import fields, models


class AccountInvoiceReport(models.Model):
    """This class inherits the model 'account.invoice.report'"""
    _inherit = 'account.invoice.report'

    discount = fields.Float('Discount', readonly=True,
                            help="Specify the discount.")

    def _select(self):
        """This allows the report to include the discount information in its
         SQL query when fetching data from the database. """
        res = super(AccountInvoiceReport, self)._select()
        select_str = res + """, line.discount AS discount """
        return select_str
