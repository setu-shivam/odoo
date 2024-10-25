# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SetuProcessHistoryLine(models.Model):
    _name = "setu.process.history.line"
    _description = "Process History Line"

    order_ref = fields.Char(string='Order Reference', translate=True)
    default_code = fields.Char(string='SKU', translate=True)
    message = fields.Text(string="Message", translate=True)
    record_id = fields.Integer(string="Record ID")

    model_id = fields.Many2one("ir.model", string="Model")
    product_id = fields.Many2one('product.product', 'Product')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    setu_ecommerce_product_chain_line_id = fields.Many2one("setu.ecommerce.product.chain.line",
                                                           string="e-Commerce Product Chain Line")
    setu_ecommerce_order_chain_line_id = fields.Many2one("setu.ecommerce.order.chain.line",
                                                         string="e-Commerce Order Chain Line")
    setu_ecommerce_customer_chain_line_id = fields.Many2one("setu.ecommerce.customer.chain.line",
                                                            string="e-Commerce Customer Chain Line")
    process_history_id = fields.Many2one('setu.process.history', string="Process History", ondelete="cascade")

    @api.model
    def get_model_id(self, model_name):
        ir_mode_obj = self.env['ir.model']
        ir_model_id = ir_mode_obj.search([('model', '=', model_name)])
        if ir_model_id:
            return ir_model_id.id
        return False

    def create_process_history_line(self, message, model_id, record_id, process_history_id, default_code='',
                                    order_ref='', product_id=False):
        vals = {'message': message,
                'default_code': default_code,
                'order_ref': order_ref,
                'product_id': product_id and product_id.id or False,
                'model_id': model_id,
                'record_id': record_id.id if record_id else False,
                'process_history_id': process_history_id.id if process_history_id else False}
        process_history_id = self.create(vals)
        return process_history_id
