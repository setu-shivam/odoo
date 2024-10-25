# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Inventory Coverage + ABC Analysis Report',
    'version': '18.0',
    'price': 49,
    'currency': 'EUR',
    'category': 'stock',
    'summary': """	
        Inventory Coverage ABC Analysis Report is used to for view current stock, average daily sale order and coverage days and all information from ABC report
        Inventory Coverage Analysis Report is used to check Current Stock, Average Daily Sales and Coverage Days
        Inventory coverage days, coverage report, inventory management, stock management, stock analysis, inventory analysis, manage 
        inventory, our of stock days, work accuracy, vendor strategy, static coverage days, real time stock visibility, vendor selection 
        strategy, number of days remaining for current stock inventory, reorder planning, vendor based selection, analyse coverage days, 
        inventory coverage ratio,
		""",
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',
    'description': """
        Inventory Coverage Analysis Report is used to for view current stock, average daily sale order and coverage days and all information from ABC report
    """,
    'images': ['static/description/banner.gif'],
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'license': 'OPL-1',
    'sequence': 25,
    'depends': ['setu_inventory_coverage_report', 'setu_abc_analysis_reports'],
    'data': [
        'db_function/get_inventory_coverage_abc_analysis_data.sql',
        'wizard/setu_inventory_coverage_abc_report.xml',
    ],
    'application': True,
}
