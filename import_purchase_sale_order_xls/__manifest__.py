# coding: utf-8


{
    'name': 'Import Purchase / Sale Order lines .XLS(x)',
    'version': '10.0.1.0.0',
    'author': 'fed_imad@hotmail.fr',
    'website': 'https://github.com/fedimad/odoo_modules',
    'license': 'AGPL-3',
    'category': 'Sales,Purchase',
    'summary': "Import a purchase & a sale order from an .xls/.xlsx file",
    'depends': ['base',
                'sale',
                'purchase',
                'web'
                ],
    'data': [

        'views/import_bc.xml',

        'wizard/import_purchase_order.xml',
        'wizard/import_sale_order.xml',
    ],

    'qweb': ['static/src/xml/import_cmd.xml'],
    'images': ['static/description/banner.jpg'],

    'installable': True,
    'application': True,
    'demo': [],
    'test': []
}
