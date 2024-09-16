# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

from odoo import api, exceptions, fields, models, _

import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import datetime
import operator as py_operator
import logging
_logger = logging.getLogger(__name__)



class SaleOrder(models.Model):
    _inherit = "sale.order"


    public_pricelist = fields.Boolean(string='Liste de prix publique', default=False, store=True)


    discount_user = fields.Boolean('Authorized discount user', compute='_check_if_authorized_user', store=True)


    @api.depends('partner_id','order_line')
    def _check_if_authorized_user(self):
        check_user = self.env['discount.limit'].search([('user_ids','in',self.env.user.id)],limit=1)
        if check_user :
            self.discount_user = True
        else:
            self.discount_user = False



    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()

        if self.partner_id:
            self.client_order_ref = self.partner_id.ref
            for rec in self:
                rec.public_pricelist = rec.pricelist_id.is_public




class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id','discount')
    def _onchange_discount(self):
        public_pricelist_id = False

        allowed_discount = self.env['discount.limit'].search([('user_ids','=',self.env.user.id)],limit=1)
        public_pricelist_id = self.order_id.pricelist_id.is_public

        if  public_pricelist_id:
            if allowed_discount:
                # self.discount = 0.0
                pricelist_id = allowed_discount.allowed_discount
                if not (self.product_id and self.product_uom and
                    self.order_id.partner_id and pricelist_id and
                    pricelist_id.discount_policy == 'without_discount' and
                    self.env.user.has_group('product.group_discount_per_so_line')):
                    return
                product = self.product_id.with_context(
                    lang=self.order_id.partner_id.lang,
                    partner=self.order_id.partner_id,
                    quantity=self.product_uom_qty,
                    date=self.order_id.date_order,
                    pricelist=pricelist_id.id,
                    uom=self.product_uom.id,
                    fiscal_position=self.env.context.get('fiscal_position')
                )

                product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)

                price, rule_id = pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
                new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, pricelist_id.id)

                if new_list_price != 0:
                    if pricelist_id.currency_id != currency:
                        # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                        new_list_price = currency._convert(
                            new_list_price, pricelist_id.currency_id,
                            self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
                    discount = (new_list_price - price) / new_list_price * 100
                    
                if self.discount > discount:
                    raise exceptions.UserError(
                        _("Vous n'êtes pas autorisé à appliquer une remise supérieure à %s%%.\n"
                          "Veuillez contacter votre superviseur.",
                          round(discount, 2)))
        else:
            self.discount = 0.0
            if not (self.product_id and self.product_uom and
                    self.order_id.partner_id and self.order_id.pricelist_id and
                    self.order_id.pricelist_id.discount_policy == 'without_discount' and
                    self.env.user.has_group('product.group_discount_per_so_line')):
                return
            pricelist_id = self.order_id.pricelist_id.id
            self.discount = 0.0
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=pricelist_id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )

            product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)

            price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
            new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.order_id.pricelist_id.id)

            if new_list_price != 0:
                if self.order_id.pricelist_id.currency_id != currency:
                    # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                    new_list_price = currency._convert(
                        new_list_price, self.order_id.pricelist_id.currency_id,
                        self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
                discount = (new_list_price - price) / new_list_price * 100
                if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                    self.discount = discount





