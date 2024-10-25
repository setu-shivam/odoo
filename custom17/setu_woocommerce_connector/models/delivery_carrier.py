from odoo import fields, models, api


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    woocommerce_delivery_code = fields.Char(string="WooCommerce Delivery Code", help="WooCommerce Delivery Code",
                                            translate=True)
