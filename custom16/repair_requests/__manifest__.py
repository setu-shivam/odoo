{
    'name': 'repair_requests',
    'version': '16.1',
    'depends': ['mail','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/repair_requests_requests_view.xml',
        'views/repair_requests_services_view.xml',
        'views/repair_requests_status_view.xml',
        'views/product_template.xml',
    ]
}
