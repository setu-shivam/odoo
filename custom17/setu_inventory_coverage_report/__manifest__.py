# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inventory Coverage Analysis Report',
    'version': '17.0',
    'price': 155,
    'currency': 'EUR',
    'category': 'stock',
    'summary': """
        Inventory Coverage Analysis Report is used to check Current Stock, Average Daily Sales and Coverage Days
        Inventory coverage days, coverage report, inventory management, stock management, stock analysis, inventory analysis, manage 
        inventory, our of stock days, work accuracy, vendor strategy, static coverage days, real time stock visibility, vendor selection 
        strategy, number of days remaining for current stock inventory, reorder planning, vendor based selection, analyse coverage days, 
        inventory coverage ratio,
    """,
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'description': """
        Inventory Coverage Analysis Report is used to check Current Stock, Average Daily Sales and Coverage Days
        The Inventory Coverage Days Report Application – A powerful that utilizes historical sales data to calculate average daily sales. Through 
        analysis of on-hand quantities, this solution offers a clear roadmap. It enables businesses to precisely determine the coverage days their 
        current stock can sustain
    """,
    'images': ['static/description/banner.gif'],
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 25,
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard_views/setu_inventory_coverage_report.xml',
        'db_function/get_sales_production_transaction_data.sql',
        'db_function/get_current_stock_data.sql',
        'db_function/get_inventory_coverage_data.sql',
        'db_function/get_stock_data.sql',
    ],
    'application': True,
}
