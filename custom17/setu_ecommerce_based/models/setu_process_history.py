# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SetuProcessHistory(models.Model):
    _name = "setu.process.history"
    _description = "Process History"
    _inherit = ["mail.thread"]
    _order = 'id desc'

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string='History Number', default='/', copy=False, required=True, translate=True)
    record_id = fields.Integer(string="Record ID")
    history_perform = fields.Selection(
        [('import', 'Import'), ('export', 'Export'), ('cancel', 'Cancel'), ('update', 'Update'),
         ('refund', 'Refund'), ('conn', 'Connection'), ('prepare_create', 'Prepare Create'),
         ('prepare_update', 'Prepare Update'), ('record_fetch', 'Fetch')], string="Operation Perform")
    message = fields.Text(string="History Message", translate=True)
    model_id = fields.Many2one("ir.model", string="Model")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False, default='none')
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)
    process_history_line_ids = fields.One2many('setu.process.history.line', 'process_history_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env["ir.sequence"].next_by_code("setu.process.history") or "/"
            vals.update({"name": name or ""})
        return super(SetuProcessHistory, self).create(vals_list)
