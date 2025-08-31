# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    """Inherit 'purchase.order' model and add fields needed"""
    _inherit = "purchase.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            # Calculate discount (like in your first function)
            amount_discount = sum(
                (line.product_uom_qty * line.price_unit * line.discount) / 100
                for line in order_lines
            )

            # Assign values to fields
            if order.currency_id.compare_amounts(order.amount_untaxed, amount_untaxed):
                order.amount_untaxed = amount_untaxed
                order.amount_tax = amount_tax
                order.amount_discount = amount_discount  # new field must exist in model
                order.amount_total = order.amount_untaxed + order.amount_tax



    state = fields.Selection(selection_add=[
        ('waiting', 'Waiting Approval'),
    ], string='Status', readonly=True, copy=False, index=True,
        default='draft', help="Status of quotation.")
    discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Discount type',
        default='percent', help="Type of discount.")
    discount_rate = fields.Float('Discount Rate', digits=(16, 2),
                                 help="Give the discount rate.")
    amount_discount = fields.Monetary(string='Discount', store=True,
                                      compute='_amount_all', readonly=True,
                                      help="Give the amount to be discounted.")
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True,
                                     readonly=True, compute='_amount_all',
                                     help="Untaxed amount displayed.")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True,
                                 compute='_amount_all',
                                 help="Taxes of product.")
    amount_total = fields.Monetary(string='Total', store=True, readonly=True,
                                   compute='_amount_all',
                                   help="Total amount provided.")



    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        """This function calculates supply rates based on change of
                discount_type, discount_rate and invoice_line_ids"""
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = discount = 0.0
                for line in order.order_line:
                    total += round((line.product_uom_qty * line.price_unit))
                if order.discount_rate != 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount
                    new_sub_price = (line.price_unit * (discount / 100))
                    line.total_discount = line.price_unit - new_sub_price


    def _prepare_invoice(self, ):
        """Super sale order class and update with fields"""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate,
            'amount_discount': self.amount_discount,
        })
        return invoice_vals

    def button_dummy(self):
        """The button_dummy method is intended to perform some action related
          to the supply rate and always return True"""
        self.supply_rate()
        return True
