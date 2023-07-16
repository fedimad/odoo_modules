# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
#    Odoo                                                                    #
#    Copyright (C) 2023-2024 Feddad Imad (feddad.imad@gmail.com)             #
#                                                                            #
##############################################################################

{
    'name': 'Firebase Push Notification',
    'version': '1.0',
    'category': 'Mail',
    'author': 'feddad.imad@gmail.com',
    'summary': 'Mail',
    'description': """
Provide free unlimited push notifications on android phones, absolutely free,
which free android App (used Firebase Push Notifications)
    """,
    'depends': ['base','web','mail'],
    'data': [

        'security/mobile_app_security.xml',
        'security/ir.model.access.csv',

        'views/res_partner.xml',
        'views/mobile_app_view.xml',
        'views/mobile_app_notif_log_partner.xml',

    ],
    'demo': [
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
