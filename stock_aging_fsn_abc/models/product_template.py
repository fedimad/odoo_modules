# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_obsolete = fields.Boolean(
        string='Obsolete',
        copy=False,
        help="Set by the Inventory Aging report when the whole remaining stock "
             "of the product sits in the oldest age bucket. It never archives "
             "or deletes the product: you decide what to do with it.",
    )
