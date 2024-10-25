# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuEcommerceCustomerChainLine(models.Model):
    _name = 'setu.ecommerce.customer.chain.line'
    _description = 'eCommerce Customer Chain Line'

    name = fields.Char(string="Customer Chain Line", translate=True)
    ecommerce_customer_id = fields.Char(string="Customer Chain Line ID", translate=True)
    state = fields.Selection([("draft", "Draft"), ("fail", "Fail"), ("done", "Done"), ("cancel", "Cancelled")],
                             default="draft")
    customer_chain_line_data = fields.Text(string="Customer Chain Line Data")
    last_customer_chain_process_date = fields.Datetime(string="Last Chain Line Process Date")
    setu_ecommerce_customer_chain_id = fields.Many2one("setu.ecommerce.customer.chain", string="Customer Chain ID",
                                                       required=True, ondelete="cascade", copy=False)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if self._check_process_line():
            raise ValidationError(_('You can not remove processed chain line'))

    def _check_process_line(self):
        return self.filtered(lambda process_line_id: process_line_id.state == 'done')

    def initialize_ecommerce_process_customer_chain_line(self, customer_chain_ids):
        for customer_chain_id in customer_chain_ids:
            line_ids = customer_chain_id.setu_ecommerce_customer_chain_line_ids.filtered(
                lambda line_id: line_id.state == "draft")
            customer_chain_id.no_records_processed += 1
            if customer_chain_id.no_records_processed > 4:
                customer_chain_id.is_action_require = True
                note = (_("<p>The connector tried to run the order queue multiple times but due to missing information,"
                          " could not process this queue. You need to run this queue manually.</p>"))
                customer_chain_id.message_post(body=note)
                continue
            self._cr.commit()
            line_ids.ecommerce_process_customer_chain_line()
        return True

    @api.model
    def cron_auto_import_ecommerce_customer_chain_line(self):
        multi_ecommerce_connector_ids = self.search([('state', '=', 'draft')]).mapped('multi_ecommerce_connector_id')
        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            if hasattr(self,
                       '%s_auto_process_ecommerce_customer_chain_line' % multi_ecommerce_connector_id.ecommerce_connector):
                getattr(self,
                        '%s_auto_process_ecommerce_customer_chain_line' % multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def ecommerce_create_customer_chain_line(self, setu_ecommerce_customer_chain_id, customer_chain_lst):
        if hasattr(self,
                   '%s_process_ecommerce_create_customer_chain_line' % setu_ecommerce_customer_chain_id.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_process_ecommerce_create_customer_chain_line' % setu_ecommerce_customer_chain_id.multi_ecommerce_connector_id.ecommerce_connector)(
                setu_ecommerce_customer_chain_id, customer_chain_lst)
        return True

    def ecommerce_process_customer_chain_line(self):
        if hasattr(self,
                   '%s_process_ecommerce_customer_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_process_ecommerce_customer_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True
