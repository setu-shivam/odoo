# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SetuEcommerceCustomerChain(models.Model):
    _name = 'setu.ecommerce.customer.chain'
    _description = 'eCommerce Customer Chain'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    is_chain_in_process = fields.Boolean(string="Is Chain Processing", default=False)
    is_action_require = fields.Boolean(default=False)
    current_status = fields.Char(default="Running...", translate=True)
    name = fields.Char(readonly=True, translate=True)
    record_created_from = fields.Selection([("import_process", "Via Import Process"), ("webhook", "Via Webhook")])
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("completed", "Completed"), ("fail", "Fail")],
        compute="_get_customer_chain_state", default="draft", store=True, tracking=True)
    no_records_processed = fields.Integer(string="No Records Processed")
    total_customer_records = fields.Integer(string="Total Record", compute="_get_total_count_customer_records")
    total_draft_customer_records = fields.Integer(string="Total Draft Records",
                                                  compute="_get_total_count_customer_records")
    total_done_customer_records = fields.Integer(string="Total Done Records",
                                                 compute="_get_total_count_customer_records")
    total_fail_customer_records = fields.Integer(string="Total Fail Records",
                                                 compute="_get_total_count_customer_records")
    total_cancel_customer_records = fields.Integer(string="Total Cancel Records",
                                                   compute="_get_total_count_customer_records")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)
    process_history_id = fields.Many2one("setu.process.history", string="Process History")
    process_history_line_ids = fields.One2many(related="process_history_id.process_history_line_ids")
    setu_ecommerce_customer_chain_line_ids = fields.One2many("setu.ecommerce.customer.chain.line",
                                                             "setu_ecommerce_customer_chain_id",
                                                             string="Customers Lines")

    @api.depends("setu_ecommerce_customer_chain_line_ids.state")
    def _get_total_count_customer_records(self):
        for customer_chain_id in self:
            chain_line_ids = customer_chain_id.setu_ecommerce_customer_chain_line_ids
            customer_chain_id.total_customer_records = len(chain_line_ids)
            customer_chain_id.total_draft_customer_records = len(
                chain_line_ids.filtered(lambda line_id: line_id.state == "draft"))
            customer_chain_id.total_done_customer_records = len(
                chain_line_ids.filtered(lambda line_id: line_id.state == "done"))
            customer_chain_id.total_fail_customer_records = len(
                chain_line_ids.filtered(lambda line_id: line_id.state == "fail"))
            customer_chain_id.total_cancel_customer_records = len(
                chain_line_ids.filtered(lambda line_id: line_id.state == "cancel"))

    @api.depends("setu_ecommerce_customer_chain_line_ids.state")
    def _get_customer_chain_state(self):
        for customer_chain_id in self:
            if customer_chain_id.total_customer_records == customer_chain_id.total_done_customer_records + customer_chain_id.total_cancel_customer_records:
                customer_chain_id.state = "completed"
            elif customer_chain_id.total_draft_customer_records == customer_chain_id.total_customer_records:
                customer_chain_id.state = "draft"
            elif customer_chain_id.total_customer_records == customer_chain_id.total_fail_customer_records:
                customer_chain_id.state = "fail"
            else:
                customer_chain_id.state = "in_progress"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            seq = self.env["ir.sequence"].next_by_code("setu.ecommerce.customer.chain") or "/"
            vals.update({"name": seq or ""})
        return super(SetuEcommerceCustomerChain, self).create(vals_list)

    def ecommerce_process_create_customer_chain(self, multi_ecommerce_connector_id, record_created_from):
        return self.create(
            {"multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
             "record_created_from": record_created_from})

    def action_redirect_customer_process_history(self):
        return {'name': _('Process History Line'),
                'view_mode': 'tree',
                'res_model': 'setu.process.history.line',
                'view_id': self.env.ref('setu_ecommerce_based.setu_process_history_line_tree_view').id,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.process_history_line_ids.ids)]}
