# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com

{
    'name': "Algérie - CODE CNRC",
    'version': '24.1',
    'category': 'Accounting',
    'description': """
This is the module to manage CNRC Codes for Algeria in Odoo.
========================================================================

This module applies to companies based in Algeria.
.

**Email:** feddad.imad@gmail.com
""",
    'author': 'feddad.imad@gmail.com',
    'depends': ['account','base'],
    'data': [
	    'security/ir.model.access.csv',
        'data/activity_code_data.xml',
        'views/activity_code.xml',
        'views/res_partner.xml',
    ],
    'images': ['static/description/banner.gif'],

    'installable': True,
    'application': False,
    'auto_install': False,
}

