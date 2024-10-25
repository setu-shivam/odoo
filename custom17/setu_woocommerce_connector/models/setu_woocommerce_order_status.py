from odoo import fields, models


class SetuWooCommerceOrderStatus(models.Model):
    _name = 'setu.woocommerce.order.status'
    _description = 'WooCommerce Order Status'

    name = fields.Char(string="Name")
    status = fields.Char(string="Status")
