{
    # App information
    'name': 'e-Commerce Base',
    'version': '1.1',
    'category': 'Sale',
    'license': 'OPL-1',
    'price': 20,
    'currency': 'EUR',

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',

    # Dependencies
    'depends': ['delivery', 'sale_stock', 'account', 'sale_management'],

    'summary': """ 
        eCommerce base is one such solution that now allows users to configure various common setup of Company, Warehouse, 
        Creating Products between online eCommerce store and ERP, validating Inventory, stock fields, Product’s description on ERP and 
        multiple online stores, Selecting sales team for approvals of various orders, payment related work and various configurations in ERP 
        for multiple online stores all together through this single solution. woocommerce, connector, shopify connector, wayfair, shopify, 
        integration, Thus now much of the time of the owner of Multiple online stores is saved as all configurations common for multiple 
        eCommerce platforms is configured in ERP through this single solution.
        """,

    'description': """ 
        eCommerce base is one such solution that now allows users to configure various common setup of Company, Warehouse, 
        Creating Products between online eCommerce store and ERP, validating Inventory, stock fields, Product’s description on ERP and 
        multiple online stores, Selecting sales team for approvals of various orders, payment related work and various configurations in ERP 
        for multiple online stores all together through this single solution. 
        Thus now much of the time of the owner of Multiple online stores is saved as all configurations common for multiple 
        eCommerce platforms is configured in ERP through this single solution.
        """,

    'images': ['static/description/banner.png'],
    'sequence': 31,

    # View
    'data': ['security/setu_ecommerce_based_security.xml',
             'security/ir.model.access.csv',
             'data/setu_sale_order_automation_data.xml',
             'data/setu_ecommerce_sequence_data.xml',
             'data/setu_ecommerce_product_data.xml',
             'data/setu_ir_cron.xml',
             'views/setu_sale_order_automation_views.xml',
             'views/product_product_views.xml',
             'views/sale_order_views.xml',
             'views/setu_multi_ecommerce_connector_views.xml',
             'views/setu_process_history_views.xml',
             'views/setu_process_history_line_views.xml',
             'wizard_views/setu_ecommerce_import_export_process_wiz_views.xml',
             'wizard_views/setu_cron_configuration_wiz_views.xml',
             'views/setu_generic_product_image_views.xml',
             'views/stock_quant_views_extended.xml',
             'wizard_views/setu_ecommerce_process_chain_wiz_views.xml',
             'wizard_views/setu_ecommerce_product_export_wiz_views.xml',
             'views/setu_ecommerce_customer_chain_views.xml',
             'views/setu_ecommerce_order_chain_views.xml',
             'views/setu_ecommerce_product_chain_views.xml',
             ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
    'active': False,

}
