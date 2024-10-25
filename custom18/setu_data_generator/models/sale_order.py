# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_allow_child_company_journal = fields.Boolean(default=False, copy=False)

    def _prepare_confirmation_values(self):
        """
        Use: Check history order from data generator module
        """
        values = super(SaleOrder, self)._prepare_confirmation_values()
        context = self.env.context
        is_history_order = context.get('history_order', False)
        if not is_history_order:
            values.update({'date_order': self.date_order})
        return values

    def action_confirm(self):
        """
        Purpose : This method is used for confirmed sale orders
                -This method is used for set sale order state as 'sale'
        :return:
        """
        if not self._context.get('history_order', False):
            return super(SaleOrder, self).action_confirm()

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale'
        })
        self._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True

