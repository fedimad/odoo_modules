# -*- coding: utf-8 -*-
#############################################################################
{
    'name': 'User Log Details | Sessions Management | Track Logins | End Sessions | Audit login',
    'version': '17.0.1.0.0',
    'category': 'System',
    'summary': 'Login user details.',
    'description': """This module captures and stores user login details,
    including username, login date and IP address, and browser by providing a comprehensive
    record of user login activities.""",
    'author': 'feddad.imad@gmail.com',
    'website': "",
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/login_detail_views.xml',
        'views/res_users_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
