# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2019  -

{
    'name': 'Algerie - Timbre Fiscal Avec écriture',
    'version': '0.4',
    'author': '< Fed_imad@hotmail.fr > < toufik.aimar@gmail.com >',
    'website': '',
    'category': 'Accounting',
    'summary': 'Timbre avec ecriture comptable',
    'description': """
This is the module to manage the Fiscal Timbre in Odoo With Timbre As Account Move Line.
========================================================================

This module applies to companies based in Algeria.
.

""",

    'depends': ['l10n_dz'],
    'data': [

	'data/timbre_data.xml',

    'security/ir.model.access.csv',

	'views/timbre_view.xml',
    'views/sale_view.xml',
	'views/purchase_view.xml',
	'views/payment_invoice_view.xml',

    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
