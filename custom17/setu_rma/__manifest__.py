{
    # App information
    'name': 'RMA / Website RMA (Return Merchandise Authorization)',
    'version': '17.1',
    'price': 119,
    'currency': 'EUR',
    'category': 'Sales',
    'license': 'OPL-1',
    'sequence': 27,

    # Author
    'author': 'Setu Consulting Services Pvt. Ltd.',
    'maintainer': 'Setu Consulting Services Private Limited',
    'website': 'https://www.setuconsulting.com/',

    # Dependencies
    'depends': ['delivery', 'sales_team', 'repair'],

    'summary': """  
        RMA / Website rma - Return Merchandise Authorization is an application that helps to manage the return product process and to do analysis over the reason
        for return products or return order. It facilitates to return the product with selecting options to Repair product, 
        Replace or replacement product, Buy Back rather than refund requests every time. It generates return invoice, 
        refund invoice for refund product request, buyback invoice and Repair invoice for repair products request. 
        Sale order for Replace product request, buy back request. RMA / website rma in odoo provides authoritative power to the manager or 
        user to validate the return request. Thus, the return product procedure can be handled in a fully automated process. 
        Also, the reason for return can help to do analysis over return products that helps to  improve the business operation.
        """,

    'support': 'support@setuconsulting.com',
    'description': """
        The RMA / Website RMA system vastly simplifies the entire returns process by providing you with an interface to communicate with the customer, 
        and gives you the power to accept or reject the return based on criteria you set, To facilitate the Return Policy, manual work of returning products is impossible to implement, 
        Maintaining the database like type of product, brand, reason, frequency of Return Products emphasizes attention to design a solution 
        which reduces the manual process, and also validates whether the product should be accepted for return or return order not and also generation of analytical 
        report over return products to take necessary actions if any to maintain revenue. 
    """,

    'data': ['security/setu_rma_group.xml',
             'security/ir.model.access.csv',

             'report/rma_report.xml',
             'report/rma_report_template.xml',

             'views/setu_rma_dashboard_views.xml',

             'data/setu_return_order_reason.xml',
             'data/setu_return_reason.xml',
             # 'data/mail_template_data.xml',
             'data/setu_return_order_sequence.xml',

             'wizard_views/claim_process_wizard_views.xml',

             'views/account_move_views.xml',
             'views/sale_order_views.xml',
             'views/setu_return_order_reason_views.xml',
             'views/setu_return_order_reject_views.xml',
             'views/setu_return_order_views.xml',
             'views/stock_picking_views.xml',
             'views/stock_warehouse_views.xml',
             'views/setu_return_reason_views.xml',
             'views/setu_rma_menu.xml',
             'views/repair_order_views.xml',
             'views/res_config_setting.xml',
             'views/return_order_template_view.xml',
             ],

    'assets': {
        'web.assets_backend': [
            'setu_rma/static/src/scss/main.scss',
            'setu_rma/static/src/js/moment.js',
            'setu_rma/static/src/js/rma_dashboard.js',
            'setu_rma/static/src/xml/*',
        ],
    },

    # Odoo Store Specific
    'images': ['static/description/banner.gif'],

    # Technical
    'installable': True,
    'auto_install': False,
    'application': True,
    'active': False,
    'live_test_url': 'https://www.youtube.com/playlist?list=PLH6xCEY0yCIAieyNZgv4coOp9Spw1c_n8',
}
