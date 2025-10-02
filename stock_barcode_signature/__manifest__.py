# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

{
    'name': 'Stock Barcode Signature',
    'version': '1.0',
    'summary': 'Allow Signature in barcode app',
    'category': "Inventory",
    'description': """
Allow user to add signature when validating a stock picking in stock barcode applicatation
==========================================================================================




Main Features
-------------
    * Add signature to stock picking barcode app

Required modules:
    * stock
    * stock_barcode

**Email:** feddad.imad@gmail.com
    """,
    'author': 'feddad.imad@gmail.com',
    'website': '',
    'sequence': 0,
    'depends': ['base','stock','stock_barcode','web'],
    'demo': [],
    'data': [

    ],

    'assets': {
        'web.assets_backend': [
            'stock_barcode_signature/static/src/signature_button.js',
            'stock_barcode_signature/static/src/add_signature_button.xml',
        ],
    },
    'qweb': [],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
