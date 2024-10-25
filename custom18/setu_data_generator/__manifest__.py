# -*- coding: utf-8 -*-
{
    'name': "setu_data_generator",
    'summary': """This module is useful to generate past transactional data for the testing purpose""",
    'description': """
        This module allows user to create history transactional data for 
            Sales, 
            Purchase, 
            Inventory Adjustment,
            Productions,
            Internal Transfers
    """,

    'author': "Setu Consulting Services Pvt. Ltd.",
    'website': "http://www.setuconsulting.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_stock', 'purchase_stock', 'account', 'sale_management', 'accountant'],
    'images': ['static/description/images/icon.png'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/product_category.xml',
        'data/product_product.xml',
        'data/res_partner.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'wizard/view_data_generator.xml',
    ],
}
