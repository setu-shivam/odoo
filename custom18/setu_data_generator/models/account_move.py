# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _search_default_journal(self):
        res = super()._search_default_journal()
        order_id = self.invoice_line_ids.sale_line_ids.order_id or self.invoice_line_ids.purchase_line_id.order_id
        if order_id and order_id.is_allow_child_company_journal:
            journal_types = 'sale' if order_id._name == 'sale.order' else 'purchase'
            journal = self.env['account.journal'].search(
                [('company_id', '=', self.company_id.id), ('type', '=', journal_types)], limit=1)
            if not journal:
                raise UserError(res._build_no_journal_error_msg(self.company_id.display_name, [journal_types]))
            res = journal
        return res
