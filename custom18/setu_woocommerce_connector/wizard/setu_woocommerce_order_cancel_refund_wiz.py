# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
import requests
from odoo.exceptions import ValidationError


class SetuWooCommerceOrderCancelRefundWiz(models.TransientModel):
    _name = 'setu.woocommerce.order.cancel.refund.wiz'
    _description = 'WooCommerce Order Cancel Refund'

    is_auto_create_credit_note = fields.Boolean(string="Is Create Auto Credit Note", default=False)
    woocommerce_order_note = fields.Char(string="WooCommerce Order Note", translate=True)
    refund_date = fields.Date(string="Refund Date", default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 help='You can select here the journal to use for the credit note that '
                                      'will be created. If you leave that field empty, it will use the same journal '
                                      'as the current invoice.')

    def action_cancel_refund_woocommerce_order(self):
        active_id = self._context.get('active_id')
        order_id = self.env['sale.order'].browse(active_id)
        multi_ecommerce_connector_id = order_id.multi_ecommerce_connector_id
        wcapi = multi_ecommerce_connector_id.connect_with_woocommerce()
        info = {'status': 'cancelled'}
        info.update({'id': order_id.ecommerce_order_id})
        response = wcapi.post('orders/batch', {'update': [info]})
        if not isinstance(response, requests.models.Response):
            raise ValidationError(_("Cancel Order \nResponse is not in proper format :: %s" % (response)))
        if response.status_code in [200, 201]:
            order_id.write({'is_order_cancelled_in_woocommerce': True})
        else:
            raise ValidationError(_("Error in Cancel Order %s" % (response.content)))
        try:
            result = response.json()
        except Exception as e:
            raise ValidationError(_("Error : While Cancel order %s to WooCommerce for Multi e-Commerce %s. \n%s" %
                                    order_id.ecommerce_order_id, multi_ecommerce_connector_id.name, e))

        if self.is_auto_create_credit_note:
            info = {'status': 'refunded'}
            info.update({'id': order_id.ecommerce_order_id})
            response = wcapi.post('orders/batch', {'update': [info]})
            if not isinstance(response, requests.models.Response):
                raise ValidationError(_("Cancel Order \nResponse is not in proper format :: %s" % (response)))
            if response.status_code in [200, 201]:
                self.create_woocommerce_sale_order_refund(order_id)
        return True

    def create_woocommerce_sale_order_refund(self, order_id):
        moves = order_id.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice' and m.payment_state == 'paid')
        if not moves:
            warning_message = "The order is cancelled or refunded on the WooCommerce store, but no invoice is " \
                              "generated in Odoo. So, you can't generate credit note."
            raise ValidationError(_(warning_message))
        default_values_list = []
        for move in moves:
            default_values_list.append({
                'ref': _('Reversal of: %s, %s') % (move.name, self._message_get_default_recipients()) if self._message_get_default_recipients() else _('Reversal of: %s') % (move.name),
                'date': self.refund_date or move.date,
                'invoice_date': move.is_invoice(include_receipts=True) and (self.refund_date or move.date) or False,
                'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
                'invoice_payment_term_id': None,
                'auto_post': True if self.refund_date > fields.Date.context_today(self) else False})
        moves._reverse_moves(default_values_list)
        return True
