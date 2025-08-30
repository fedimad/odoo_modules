# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2025-2026 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

{
    'name': 'Purchase Discount on Total Amount',
    'version': '17.0.1.1.1',
    'category': 'Inventory/Purchase',
    'summary': "Discount on Total in Purchase and Invoice With Discount Limit ",
    'description': "This module is designed to manage discounts on the total "
                   "amount in purchases. It will include features to apply "
                   "discounts either as a specific amount or a percentage. "
                   "This module will enhance the functionality of Odoo's purchases"
                   "module, allowing users to easily manage and apply discounts"
                   " to purchase orders based on their requirements.",
    'author': 'feddad.imad@gmail.com',
    'company': 'FennecEvolution Technlogy',
    'maintainer': 'feddad.imad@gmail.com',
    'website': "",
    'depends': ['purchase', 'account'],
    'data': [
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/account_move_templates.xml',
        'views/purchase_order_template.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
