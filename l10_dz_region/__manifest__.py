# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Copyright (c) 2022  - feddad.imad@gmail.com

{
    'name': "Algérie - 58 Wilaya d'alger",
    'version': '22.1',
    'category': 'Accounting',
    'description': """
This is the module to manage the wilaya & commune for Algeria in Odoo.
========================================================================

This module applies to companies based in Algeria.
.

**Email:** imad.feddad@hotmail.fr
""",
    'author': 'imad.feddad@hotmail.fr, Prodigital',
    'website': 'https://prodigital.dz/',
    'depends': ['sale'],
    'data': [
	'security/ir.model.access.csv',
        'data/wilayas_data.xml',
        'data/commune_data.xml',
	'views/res_commune.xml'
    ],

    'images': ['static/description/banner.jpg'],

    'installable': True,
    'application': False,
    'auto_install': False,
}

