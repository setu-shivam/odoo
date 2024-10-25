# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from markupsafe import Markup

class SetuEcommerceProductChainLine(models.Model):
    _name = 'setu.ecommerce.product.chain.line'
    _description = 'eCommerce Product Chain Line'

    name = fields.Char(string="Product", translate=True)
    ecommerce_product_id = fields.Char(string="Product Chain", translate=True)
    last_product_chain_update_date = fields.Char(string='Last Product Chain', translate=True)
    last_product_chain_line_process_date = fields.Datetime(string="Last Process Date")

    product_chain_line_data = fields.Text(string="Product Chain Line Data")

    state = fields.Selection([("draft", "Draft"), ("fail", "Fail"), ("done", "Done"), ("cancel", "Cancelled")],
                             default="draft", string="State")

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    setu_ecommerce_product_chain_id = fields.Many2one("setu.ecommerce.product.chain", required=True, ondelete="cascade",
                                                      copy=False)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        if self._check_process_line():
            raise ValidationError(_('You can not remove processed chain line'))

    def _check_process_line(self):
        return self.filtered(lambda process_line_id: process_line_id.state == 'done')

    @api.model
    def cron_auto_import_ecommerce_product_chain_line(self):
        multi_ecommerce_connector_ids = self.search([('state', '=', 'draft')]).mapped('multi_ecommerce_connector_id')
        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            if hasattr(self,
                       '%s_auto_process_ecommerce_product_chain_line' % multi_ecommerce_connector_id.ecommerce_connector):
                getattr(self,
                        '%s_auto_process_ecommerce_product_chain_line' % multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def initialize_ecommerce_process_product_chain_line(self, product_chain_ids):
        for product_chain_id in product_chain_ids:
            product_chain_id.no_records_processed += 1
            if product_chain_id.no_records_processed > 4:
                product_chain_id.is_action_require = True
                note = (
                    _("<p>The schedule action of e-Commerce: Process Product Queue is running on background and current"
                      " record should be time executed for more than given period. Need to process Queue manually</p>"))
                product_chain_id.message_post(body=Markup(note))
                continue
            product_chain_line_ids = product_chain_id.setu_ecommerce_product_chain_line_ids
            product_chain_line_ids.ecommerce_process_product_chain_line()
        return True

    def ecommerce_process_product_chain_line(self):
        if hasattr(self, '%s_process_product_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_process_product_chain_line' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True
