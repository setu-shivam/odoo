# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_refund_move_in_ecommerce = fields.Boolean(string="Refund Move In e-Commerce", default=False)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector')
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)

    def action_refund_order_in_ecommerce(self):
        if hasattr(self,
                   '%s_process_refund_order_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_process_refund_order_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True
