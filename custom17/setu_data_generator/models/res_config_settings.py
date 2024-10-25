from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_post_days = fields.Integer("Customer Invoice Post Days", default=60,
                                             config_parameter='setu_data_generator.invoice_post_days')

    bill_post_days = fields.Integer("Vendor Bill Post Days", default=30,
                                       config_parameter='setu_data_generator.bill_post_days')

    purchase_if_minimum_stock = fields.Integer("Purchase if product stock is less then", default=30,
                                    config_parameter='setu_data_generator.purchase_if_minimum_stock')

    sale_delivery_gap = fields.Integer("Sales Delivery Gap", default=7,
                                             config_parameter='setu_data_generator.sale_delivery_gap')