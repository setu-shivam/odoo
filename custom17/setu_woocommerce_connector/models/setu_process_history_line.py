# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime


class SetuProcessHistoryLine(models.Model):
    _inherit = "setu.process.history.line"

    def woocommerce_create_product_process_history_line(self, message, model_id, product_chain_line_id,
                                                        process_history_id, sku=""):
        vals = self.woocommerce_prepare_process_history_line_vals(message, model_id, product_chain_line_id,
                                                                  process_history_id)
        vals.update(
            {'setu_ecommerce_product_chain_line_id': product_chain_line_id.id if product_chain_line_id else False,
             "default_code": sku})
        process_history_line_id = self.create(vals)
        return process_history_line_id

    def woocommerce_prepare_process_history_line_vals(self, message, model_id, record_id, process_history_id):
        vals = {'message': message, 'model_id': model_id, 'record_id': record_id.id if record_id else False,
                'process_history_id': process_history_id.id if process_history_id else False}
        return vals

    def woocommerce_create_order_process_history_line(self, message, model_id, order_chain_line_id, process_history_id,
                                                      order_ref=""):
        if order_ref:
            process_history_line_id = self.search(
                [("message", "=", message), ("model_id", "=", model_id), ("order_ref", "=", order_ref)])
            if process_history_line_id:
                process_history_line_id.update(
                    {"write_date": datetime.now(),
                     "process_history_id": process_history_id.id if process_history_id else False,
                     "setu_woocommerce_order_chain_line_id": order_chain_line_id and order_chain_line_id.id or False})
        vals = self.woocommerce_prepare_process_history_line_vals(message, model_id, order_chain_line_id,
                                                                  process_history_id)
        vals.update({'setu_ecommerce_order_chain_line_id': order_chain_line_id and order_chain_line_id.id or False,
                     "order_ref": order_ref})
        process_history_line_id = self.create(vals)
        return process_history_line_id

    def woocommerce_create_customer_process_history_line(self, message, model_id, customer_chain_line_id,
                                                         process_history_id):
        vals = self.woocommerce_prepare_process_history_line_vals(message, model_id, customer_chain_line_id,
                                                                  process_history_id)
        vals.update(
            {'setu_ecommerce_customer_chain_line_id': customer_chain_line_id and customer_chain_line_id.id or False})
        process_history_line_id = self.create(vals)
        return process_history_line_id

    def woocommerce_common_process_history_line(self, message, model_id, process_history_id):
        vals = {"message": message, "model_id": model_id,
                'process_history_id': process_history_id and process_history_id.id}
        self.create(vals)
