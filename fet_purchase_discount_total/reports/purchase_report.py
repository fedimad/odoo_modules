# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################
from odoo import fields, models


class DiscountPurchaseReport(models.Model):
    """This class inherits 'purchase.report' and adds field discount"""
    _inherit = 'purchase.report'

    discount = fields.Float('Discount', readonly=True,
                            help="Specify the discount amount.")

    def _select(self):
        """It extends the behavior of a method in the class by adding a
         new column, discount, to the SQL query. This new column represents
         the total discount for sales transactions, calculated based on
         various factors and values related to the purchase. """
        res = super(DiscountPurchaseReport, self)._select()
        select_str = res + """,sum(l.product_uom_qty / u.factor * u2.factor * cr.rate * l.price_unit * l.discount / 100.0)
         as discount"""
        return select_str
