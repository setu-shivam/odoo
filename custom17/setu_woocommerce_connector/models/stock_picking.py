# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_delivery_updated_in_woocommerce = fields.Boolean(string="Updated Delivery In WooCommerce", default=False)
    is_woocommerce_delivery = fields.Boolean(string="WooCommerce Delivery Order", default=False)
