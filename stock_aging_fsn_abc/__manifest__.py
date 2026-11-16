# -*- coding: utf-8 -*-
{
    'name': 'Stock Aging, FSN & ABC Analysis',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'author': 'feddad.imad@gmail.com',
    'images': ['static/description/banner.png'],
    'summary': 'Inventory aging (FIFO buckets), FSN, ABC and inventory loss reports in PDF and XLSX',
    'description': """
Stock Aging, FSN & ABC Analysis
===============================
One wizard, four reports (PDF, and XLSX for the first three):

* Inventory Aging - on-hand stock split in configurable age buckets (FIFO),
  optionally per lot / serial number.
* FSN - Fast / Slow / Non-moving classification by sales velocity.
* ABC - Pareto classification by sales revenue (needs the Sales app).
* Inventory Loss - scrap and inventory adjustments with value lost.

Filter by warehouse, location, category or product. Optionally flag as
"Obsolete" the products whose whole stock sits in the oldest bucket.
""",
    'depends': ['stock','ewe_logic'],
    'data': [
         'security/ir.model.access.csv',

        'report/stock_analysis_report.xml',
        'views/product_views.xml',
        'wizard/stock_analysis_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
