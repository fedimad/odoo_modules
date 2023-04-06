# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com

{
    'name': 'Algérie - Timbre Fiscal avec écriture comptable',
    'version': '22.1',
    'category': 'Accounting',
    'description': """
This is the module to manage the Fiscal Timbre in Odoo.
========================================================================


.

**Email:** feddad.imad@gmail.com
""",
    'author': 'feddad.imad@gmail.com, Prodigital',
    'website': 'https://prodigital.dz/',
    'depends': ['sale','account','purchase', 'base'],
    'data': [

	'data/timbre_data.xml',
    'security/ir.model.access.csv',
    'data/res.bank.csv',
	'views/timbre_view.xml',
    'views/sale_invoice_view.xml',
    
    ],

    'images': ['static/description/banner.jpg'],

    'installable': True,
    'application': False,
    'auto_install': False,
}
