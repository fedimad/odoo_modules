# -*- coding: utf-8 -*-
# © 2022
#   @Feddad Imad <feddad.imad@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import logging
_logger = logging.getLogger(__name__)



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _barcode_scanned = fields.Char("Barcode Scanned",
                                   help="Value of the last barcode scanned.",
                                   store=False)

    @api.model
    def po_barcode(self, barcode, po_id):
        purchase_order = self.search([
            ('id', '=', po_id)
        ])
        if not purchase_order:
            # with asumtation Purchase Order is created
            raise UserError(_(
                'Merci de sauvegarder le Bon de commande avant de scanner !'
            ))
        product_id = self.env['product.product'].search([
            ('barcode', '=', barcode)
        ])
        purchase_order_line = purchase_order.order_line.search([
            ('product_id', '=', product_id.id), ('order_id', '=', po_id)
        ], limit=1)

        if purchase_order.state == 'draft':
            if purchase_order_line:
                product_qty = purchase_order_line.product_qty + 1
                purchase_order_line.product_qty = product_qty
            elif not product_id:
                raise UserError(_(
                    "L'article avec le code-barres [%s]  n'existe pas, contacter votre administrateur Système!" 
                ) %barcode)
            else:

                taxes = product_id.supplier_taxes_id.filtered(lambda r: not product_id.company_id or r.company_id == product_id.company_id)
                tax_ids = taxes.ids
                date = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

                line_values = {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_qty': 1,
                    'product_uom': product_id.product_tmpl_id.uom_id.id,
                    'price_unit': product_id.product_tmpl_id.list_price,
                    'order_id': purchase_order.id,
                    'date_planned': date,
                    'taxes_id' : [(6,0,tax_ids)],
                }
                purchase_order.update({'order_line': [(0, 0, line_values)]})
        else:
            raise ValidationError(_("Vous ne pouvez pas ajouter/modifier une ligne de pièce si l'état est différent de Brouillon"))




##################################################################################
##################################################################################
################################## Sale ORder ####################################
##################################################################################
##################################################################################

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _barcode_scanned = fields.Char("Barcode Scanned",
                                   help="Value of the last barcode scanned.",
                                   store=False)

    @api.model
    def so_barcode(self, barcode, po_id):
        sale_order = self.search([
            ('id', '=', po_id)
        ])
        if not sale_order:
            # with asumtation Purchase Order is created
            raise UserError(_(
                'Merci de sauvegarder le Bon de commande avant de scanner !'
            ))
        product_id = self.env['product.product'].search([
            ('barcode', '=', barcode)
        ])
        sale_order_line = sale_order.order_line.search([
            ('product_id', '=', product_id.id),  ('order_id', '=', po_id)
        ], limit=1)

        
        if sale_order.state == 'draft':
            if sale_order_line:
                product_uom_qty = sale_order_line.product_uom_qty + 1
                sale_order_line.product_uom_qty = product_uom_qty
            elif not product_id:
                raise UserError(_(
                    "L'article avec le code-barres [%s]  n'existe pas, contacter votre administrateur Système!" 
                ) %barcode)
            else:
                taxes = product_id.taxes_id.filtered(lambda r: not product_id.company_id or r.company_id == product_id.company_id)
                tax_ids = taxes.ids
                line_values = {
                    'name': product_id.name,
                    'product_id': product_id.id,
                    'product_uom_qty': 1,
                    'product_uom': product_id.product_tmpl_id.uom_id.id,
                    'price_unit': product_id.product_tmpl_id.list_price,
                    'order_id': sale_order.id,

                    # 'tax_id' : [(6,0,tax_ids)],
                }
                sale_order.update({'order_line': [(0, 0, line_values)]})
        else:
            raise ValidationError(_("Vous ne pouvez pas ajouter/modifier une ligne de pièce si l'état est différent de Brouillon") )



