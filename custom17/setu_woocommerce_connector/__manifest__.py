{
    # App information
    'name': 'Odoo Woocommerce Connector',
    'version': '1.2',
    'category': 'Sales',
    'license': 'OPL-1',
    'price': 119,
    'currency': 'EUR',

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'website': 'https://www.setuconsulting.com',
    'support': 'support@setuconsulting.com',

    # Dependencies
    'depends': ['setu_ecommerce_based'],

    'summary': """ 
        Woocommerce odoo connector is an application that helps to integrate woocommerce online store with Odoo ERP. 
        Integrating WooCommerce store with Odoo ERP helps woocommerce seller to manage various functionalities of woocommerce now directly from ERP 
        which aids not only to end users but also to the management team of woocommerce. 
        By using woocommerce connector  various functionalities like importing products and its details, publishing products to woocommerce, 
        Importing Orders to Odoo, and customer details, orders, stock details, reports, invoices, returns, refunds, point of Sale, Synchronize 
        products, manage multiple stores.
        woocommerce integration, woocommerce odoo integration, woocommerce return, woocommerce refund, odoo woocommerce refund, odoo woocommerce 
        return, woocommerce risky order, import woocommerce order, export woocommerce order, import stock, import location, import shipped orders, 
        import unshipped orders, shopify connector, odoo connector, connectors, odoo shopify connector, ecommerce connector, woocommerce connector,
        return exchange,
        """,

    'description': """ 
        Odoo WooCommerce Integrator developed by us will help you manage all Operations of your WooCommerce store in Odoo 
        by integrating the WooCommerce plugin with odoo ERP. This connector allows to perform various functionalities like 
        Importing Customer’s Data, Orders, Products and their Categories, Product Tags, Stock Details, Reports, Invoices, Returns, 
        Refunds, Exporting and Updating Products tags, Product Categories, Coupon Details, and Products Stock. 
        It also allows automation of various vital tasks like Importing Orders, their Status Update, and Stock Update functionalities 
        to ease Users' work and increase potential outcomes in business.
        """,

    'images': ['static/description/banner.gif'],
    'sequence': 29,

    # Views
    'data': [
        'security/setu_woocommerce_group_security.xml',
        'security/ir.model.access.csv',

        'data/setu_woocommerce_order_status.xml',
        'data/setu_woocommerce_connector_ir_cron.xml',
        'data/setu_woocommerce_sequence_data.xml',

        'wizard_views/setu_woocommerce_process_chain_wiz_views.xml',

        'views/setu_woocommerce_dashboard_views.xml',
        'views/setu_woocommerce_main_menu.xml',
        'views/account_move_views_extended.xml',
        'views/setu_multi_ecommerce_connector.xml',
        'views/setu_woocommerce_coupons_views.xml',
        'views/setu_woocommerce_sale_order_automation_views.xml',
        'views/setu_process_history_views_extended.xml',
        'views/setu_ecommerce_customer_chain.xml',
        'views/setu_ecommerce_product_chain.xml',
        'views/setu_ecommerce_order_chain.xml',
        'views/setu_woocommerce_coupon_chain_views.xml',
        'views/setu_woocommerce_product_image_views.xml',
        'views/setu_woocommerce_product_tags_views.xml',
        'views/setu_woocommerce_product_template_views.xml',
        'views/setu_woocommerce_product_variant_views.xml',
        'views/setu_woocommerce_payment_gateway_views.xml',
        'views/setu_woocommerce_product_attributes_views.xml',
        'views/setu_woocommerce_product_attribute_terms_views.xml',
        'views/setu_woocommerce_product_category_views.xml',
        'views/setu_woocommerce_sale_process_configuration_views.xml',
        'views/product_template_views_extended.xml',
        'views/res_partner_views_extended.xml',
        'views/sale_order_views_extended.xml',
        'views/stock_picking_views_extended.xml',

        'wizard_views/setu_woocommerce_import_export_process_wiz_views.xml',
        'wizard_views/setu_woocommerce_order_cancel_refund_wiz_views.xml',

    ],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
    'active': False,
}
