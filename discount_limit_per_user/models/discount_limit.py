# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

from odoo import api, fields, models, _

import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import datetime
import operator as py_operator
import logging
_logger = logging.getLogger(__name__)



class discount_limit(models.Model):
    _name = "discount.limit"


    user_ids = fields.Many2many('res.users', string='Utilisateurs', copy=False, required=True)
    allowed_discount = fields.Many2one('product.pricelist', 'Remise Autorisé (%)', copy=False)


class Pricelist(models.Model):
    _inherit = "product.pricelist"


    is_public = fields.Boolean('Est Publique', default=False)








