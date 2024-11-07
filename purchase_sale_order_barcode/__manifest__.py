# -*- coding: utf-8 -*-
# © 2022
#   @Feddad Imad <feddad.imad@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Purchase/Sale Barcode",
    "summary": "Add Product With Barcode at Purchase/Sale Order",
    "version": "10.0.1.0.0",
    "author": 'feddad.imad@gmail.com',
    "website": 'https://github.com/fedimad/odoo_modules',
    "category": "Purchase, Sale",
    "depends": ['purchase', 'sale', 'barcodes'],
    "description": """
The purpose of this module is to help use your barcode scanner when inserting product lines.
============================================================================================

**Email:** feddad.imad@gmail.com
""",
    "data": [
        'views/purchase_sale_order_views.xml',
        'views/template.xml',
    ],
    "images": ['static/description/icon.png'],
    "license": "AGPL-3",
    "installable": True,
    "application": True,
}
