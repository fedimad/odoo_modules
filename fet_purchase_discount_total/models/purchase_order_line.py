# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    """This class inherits "purchase.order.line" and adds fields discount,
     total_discount """
    _inherit = "purchase.order.line"

    discount = fields.Float(string='Remise (%)', digits=(16, 20), default=0.0,
                            help="Discount needed.")
    total_discount = fields.Float(string="Total Remise", default=0.0,
                                  store=True, help="Total discount can be"
                                                   "specified here.")
