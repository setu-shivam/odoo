# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class SetuEcommerceOrderChain(models.Model):
    _name = 'setu.ecommerce.order.chain'
    _description = 'eCommerce Order Chain'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    is_chain_in_process = fields.Boolean(string="Is Chain Processing", default=False)
    is_action_require = fields.Boolean(string="Action Require", default=False)
    current_status = fields.Char(default="Running...", translate=True)
    name = fields.Char(string="Name", readonly=True, translate=True)
    record_created_from = fields.Selection([("import_process", "Via Import Process"), ("webhook", "Via Webhook"),
                                            ("scheduled_action", "Via Scheduled Action")], default="import_process")
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("completed", "Completed"), ("fail", "fail")],
        tracking=True, default='draft', copy=False, compute="_compute_order_state", store=True)
    total_orders_records = fields.Integer(string='Total Records', compute='_get_total_count_orders_records')
    total_draft_order_records = fields.Integer(string='Draft Records', compute='_get_total_count_orders_records')
    total_fail_order_records = fields.Integer(string='Fail Records', compute='_get_total_count_orders_records')
    total_done_order_records = fields.Integer(string='Done Records', compute='_get_total_count_orders_records')
    total_cancel_order_records = fields.Integer(string='Cancel Records', compute='_get_total_count_orders_records')
    no_records_processed = fields.Integer(string="No Records Processed")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector')
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)
    process_history_id = fields.Many2one("setu.process.history", string="Process History")
    process_history_line_ids = fields.One2many(related="process_history_id.process_history_line_ids")
    setu_ecommerce_order_chain_line_ids = fields.One2many("setu.ecommerce.order.chain.line",
                                                          "setu_ecommerce_order_chain_id")

    @api.depends('setu_ecommerce_order_chain_line_ids.state')
    def _compute_order_state(self):
        for order_chain_id in self:
            if order_chain_id.total_orders_records == order_chain_id.total_done_order_records + order_chain_id.total_cancel_order_records:
                order_chain_id.state = "completed"
            elif order_chain_id.total_draft_order_records == order_chain_id.total_orders_records:
                order_chain_id.state = "draft"
            elif order_chain_id.total_orders_records == order_chain_id.total_fail_order_records:
                order_chain_id.state = "fail"
            else:
                order_chain_id.state = "in_progress"

    @api.depends('setu_ecommerce_order_chain_line_ids.state')
    def _get_total_count_orders_records(self):
        for order_chain_id in self:
            order_chain_line_ids = order_chain_id.setu_ecommerce_order_chain_line_ids
            order_chain_id.total_orders_records = len(order_chain_line_ids)
            order_chain_id.total_draft_order_records = len(
                order_chain_line_ids.filtered(lambda chain_id: chain_id.state == "draft"))
            order_chain_id.total_done_order_records = len(
                order_chain_line_ids.filtered(lambda chain_id: chain_id.state == "done"))
            order_chain_id.total_fail_order_records = len(
                order_chain_line_ids.filtered(lambda chain_id: chain_id.state == "fail"))
            order_chain_id.total_cancel_order_records = len(
                order_chain_line_ids.filtered(lambda chain_id: chain_id.state == "cancel"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            seq = self.env["ir.sequence"].next_by_code("setu.ecommerce.order.chain") or "/"
            vals.update({"name": seq or ""})
        return super(SetuEcommerceOrderChain, self).create(vals_list)

    def ecommerce_process_create_order_chain(self, multi_ecommerce_connector_id, orders_data, record_created_from):
        while orders_data:
            vals = {"multi_ecommerce_connector_id": multi_ecommerce_connector_id.id,
                    "record_created_from": record_created_from}
            order_data = orders_data[:50]
            if order_data:
                order_chain_id = self.create(vals)
                order_chain_id.ecommerce_process_create_order_chain_line(order_data)
                del orders_data[:50]
            return order_chain_id

    def ecommerce_process_create_order_chain_line(self, order_data):
        setu_ecommerce_order_chain_line_obj = self.env["setu.ecommerce.order.chain.line"]
        vals_list = []
        for order in order_data:
            vals_list.append(
                {"setu_ecommerce_order_chain_id": self.id,
                 "multi_ecommerce_connector_id": self.multi_ecommerce_connector_id and self.multi_ecommerce_connector_id.id,
                 "ecommerce_order_id": order["id"],
                 "order_chain_line_data": order, "name": order["number"]})
        if vals_list:
            return setu_ecommerce_order_chain_line_obj.create(vals_list)
        return False

    @api.model
    def cron_auto_import_ecommerce_order_chain(self, ctx={}):
        multi_ecommerce_connector_id = ctx.get('multi_ecommerce_connector_id')
        multi_ecommerce_connector_id = self.env['setu.multi.ecommerce.connector'].browse(multi_ecommerce_connector_id)
        if hasattr(self, '%s_import_ecommerce_order_chain' % multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_import_ecommerce_order_chain' % multi_ecommerce_connector_id.ecommerce_connector)(
                multi_ecommerce_connector_id)
        return True

    def action_redirect_order_process_history(self):
        return {'name': _('Process History Line'),
                'view_mode': 'tree',
                'res_model': 'setu.process.history.line',
                'view_id': self.env.ref('setu_ecommerce_based.setu_process_history_line_tree_view').id,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.process_history_line_ids.ids)]}
