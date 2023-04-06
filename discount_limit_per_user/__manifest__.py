# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo
#    Copyright (C) 2020-2021 Feddad Imad (fed_imad@hotmail.fr).
#
##############################################################################

{
    'name': 'Discount Limit Per User',
    'version': '1.0',
    'summary': 'Sale Discount Limit',
    'description': """
Allow User to add discount if partner has public pricelist
==========================================================




Main Features
-------------
    * Add List of users to set discount in sale order

Required modules:
    * sale

**Email:** feddad.imad@gmail.com
    """,
    'author': 'feddad.imad@gmail.com',
    'website': '',
    'category': 'Sale',
    'sequence': 0,
    'depends': ['base','sale','sales_team'],
    'demo': [],
    'data': [

        'security/ir.model.access.csv',

        'views/discount_limit.xml',
        'views/sale_order.xml',
    ],

    'qweb': [],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
}
