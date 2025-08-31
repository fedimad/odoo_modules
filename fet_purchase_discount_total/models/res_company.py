# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    """This class inherits 'res.company' and adds so_double_validation,
    so_double_validation_limit to add validation limits"""
    _inherit = 'res.company'

    so_double_validation = fields.Selection([
        ('one_step', 'Confirm sale orders in one step'),
        ('two_step', 'Get 2 levels of approvals to confirm a sale order')
    ], string="Levels of Approvals", default='one_step',
        help="Provide a double validation mechanism for sales discount.")
    so_double_validation_limit = fields.Float(
        string="Percentage of Discount that requires double validation'",
        help="Minimum discount percentage for which a double validation is "
             "required.")
