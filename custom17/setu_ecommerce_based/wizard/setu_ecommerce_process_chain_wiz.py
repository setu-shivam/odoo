# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SetuEcommerceProcessChainWiz(models.TransientModel):
    _name = 'setu.ecommerce.process.chain.wiz'
    _description = 'Setu eCommerce Process Chain'

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)

    def manual_main_chain_process(self):
        get_current_chain_process = self._context.get('current_chain_process')
        if get_current_chain_process == "manual_product_chain_process":
            self.sudo().manual_product_chain_process()
        if get_current_chain_process == "manual_customer_chain_process":
            self.sudo().manual_customer_chain_process()
        if get_current_chain_process == "manual_order_chain_process":
            self.sudo().manual_order_chain_process()

    def manual_product_chain_process(self):
        setu_ecommerce_product_chain_line_obj = self.env["setu.ecommerce.product.chain.line"]
        active_product_chain_ids = self._context.get('active_ids')
        for product_chain_id in active_product_chain_ids:
            ecommerce_product_chain_line_ids = setu_ecommerce_product_chain_line_obj.search(
                [("setu_ecommerce_product_chain_id", "=", product_chain_id), ("state", "in", ('draft', 'fail'))])
            ecommerce_product_chain_line_ids.ecommerce_process_product_chain_line()
        return True

    def manual_customer_chain_process(self):
        setu_woocommerce_customer_chain_line_obj = self.env["setu.ecommerce.customer.chain.line"]
        active_customer_chain_ids = self._context.get("active_ids")
        for customer_chain_id in active_customer_chain_ids:
            ecommerce_customer_chain_line_ids = setu_woocommerce_customer_chain_line_obj.search(
                [("setu_ecommerce_customer_chain_id", "=", customer_chain_id), ("state", "in", ["draft", "fail"])])
            ecommerce_customer_chain_line_ids.ecommerce_process_customer_chain_line()
        return True

    def manual_order_chain_process(self):
        setu_woocommerce_order_chain_line_obj = self.env["setu.ecommerce.order.chain.line"]
        active_order_chain_ids = self._context.get('active_ids')
        for order_chain_id in active_order_chain_ids:
            ecommerce_order_chain_line_ids = setu_woocommerce_order_chain_line_obj.search(
                [("setu_ecommerce_order_chain_id", "=", order_chain_id), ("state", "in", ('draft', 'fail'))])
            ecommerce_order_chain_line_ids.ecommerce_process_order_chain_line()
        return True

    def cancel_main_chain_process(self):
        get_current_chain_process = self._context.get('current_chain_process')
        if get_current_chain_process == "cancel_order_chain_process":
            self.cancel_order_chain_process()
        if get_current_chain_process == "cancel_product_chain_process":
            self.cancel_product_chain_process()
        if get_current_chain_process == "cancel_customer_chain_process":
            self.cancel_customer_chain_process()

    def cancel_order_chain_process(self):
        setu_ecommerce_order_chain_obj = self.env["setu.ecommerce.order.chain"]
        active_order_chain_ids = self._context.get('active_ids')
        order_chain_ids = setu_ecommerce_order_chain_obj.browse(active_order_chain_ids)
        for order_chain_id in order_chain_ids:
            order_chain_line_ids = order_chain_id.setu_ecommerce_order_chain_line_ids.filtered(
                lambda line: line.state in ['draft', 'fail'])
            order_chain_line_ids.write({'state': 'cancel'})
            order_chain_id.message_post(body=_("Manually set to cancel chain lines %s - ") % (
                order_chain_line_ids.mapped('ecommerce_order_id')))
        return True

    def cancel_product_chain_process(self):
        setu_ecommerce_product_chain_obj = self.env["setu.ecommerce.product.chain"]
        active_product_chain_ids = self._context.get('active_ids')
        product_chain_ids = setu_ecommerce_product_chain_obj.browse(active_product_chain_ids)
        for product_chain_id in product_chain_ids:
            product_chain_line_ids = product_chain_id.setu_ecommerce_product_chain_line_ids.filtered(
                lambda line: line.state in ['draft', 'fail'])
            product_chain_line_ids.write({'state': 'cancel'})
            product_chain_id.message_post(body=_("Manually set to cancel chain lines %s - ") % (
                product_chain_line_ids.mapped('setu_ecommerce_product_chain_id')))

        return True

    def cancel_customer_chain_process(self):
        setu_ecommerce_customer_chain_obj = self.env["setu.ecommerce.customer.chain"]
        active_customer_chain_ids = self._context.get('active_ids')
        customer_chain_ids = setu_ecommerce_customer_chain_obj.browse(active_customer_chain_ids)
        for customer_chain_id in customer_chain_ids:
            customer_chain_line_ids = customer_chain_id.setu_ecommerce_customer_chain_line_ids.filtered(
                lambda line: line.state in ['draft', 'fail'])
            customer_chain_line_ids.write({'state': 'cancel'})
        return True
