# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Stock to Sale Ratio Report',
    'version': '17.0.0.0',
    'category': 'stock',
    'summary': """ """,
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'description': """ """,
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 25,
    'depends': ['sale_stock', 'purchase_stock'],
    'images': ['static/description/banner.gif'],
    'data': [
        'security/ir.model.access.csv',
        'views/setu_stock_to_sale_report.xml',
        'views/setu_stock_to_sale_ratio_res_config.xml',
        'db_function/get_stock_to _sale_report.sql'
    ],
    'application': True,
    # 'pre_init_hook': 'pre_init',

}
