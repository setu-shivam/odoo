# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuEcommerceOrderChainLine(models.Model):
    _name = 'setu.ecommerce.order.chain.line'
    _description = 'eCommerce Order Chain Line'

    name = fields.Char(help="Order Chain Line", translate=True)
    ecommerce_order_id = fields.Char(string="eCommerce Order ID", copy=False, translate=True)
    state = fields.Selection([("draft", "Draft"), ("fail", "Fail"), ("done", "Done"), ("cancel", "Cancelled")],
                             default="draft")
    order_chain_line_data = fields.Text(string="Order Chain Line Data")
    last_order_chain_line_process_date = fields.Datetime(string="Last Chain Line Process Date")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector')
    setu_ecommerce_order_chain_id = fields.Many2one("setu.ecommerce.order.chain", string="Order Chain ID",
                                                    ondelete="cascade")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if self._check_process_line():
            raise ValidationError(_('You can not remove processed chain line'))

    def _check_process_line(self):
        return self.filtered(lambda process_line_id: process_line_id.state == 'done')

    def initialize_ecommerce_process_process_order_chain_line(self, order_chain_ids):
        for order_chain_id in order_chain_ids:
            order_chain_id.no_records_processed += 1
            if order_chain_id.no_records_processed > 4:
                order_chain_id.is_action_require = True
                note = (
                    _("<p>The connector tried to run the order queue multiple times but due to missing information "
                      "couldn’t process this queue. You need to run this queue manually.</p>"))
                order_chain_id.message_post(body=note)
                continue
            chain_line_ids = order_chain_id.setu_ecommerce_order_chain_line_ids.filtered(
                lambda ocl: ocl.state == "draft")
            chain_line_ids.ecommerce_process_order_chain_line()
        return True

    @api.model
    def cron_auto_import_ecommerce_order_chain_line(self):
        multi_ecommerce_connector_ids = self.search([('state', '=', 'draft')]).mapped('multi_ecommerce_connector_id')
        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            if hasattr(self,
                       '%s_auto_process_ecommerce_order_chain_line' % multi_ecommerce_connector_id.ecommerce_connector):
                getattr(self,
                        '%s_auto_process_ecommerce_order_chain_line' % multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def ecommerce_process_order_chain_line(self, update_order=False):
        if hasattr(self, '%s_process_order_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_process_order_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector)(
                update_order)
        return True
