# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    order_id = fields.Many2one('sale.order', string="Sale Order")
    reversal_invoice_id = fields.Many2one('account.move', string="Refund Invoice")
