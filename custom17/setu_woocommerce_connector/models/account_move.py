from odoo import fields, models, api, _
import requests
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def woocommerce_connector_process_refund_order_to_ecommerce(self):
        for account_move_id in self:
            woo_api_connect = account_move_id.setu_multi_ecommerce_connector_id.connect_with_woocommerce()
            sale_order_ids = account_move_id.invoice_line_ids.sale_line_ids.order_id
            for sale_order_id in sale_order_ids:
                data = {"amount": str(account_move_id.amount_total), 'reason': str(account_move_id.name or ''),
                        'api_refund': False}
                api_response = woo_api_connect.post('orders/%s/refunds' % sale_order_id.woocommerce_order_id, data)
                if not isinstance(api_response, requests.models.Response):
                    raise ValidationError(
                        _("Something went's to wrong. WooCommerce refund order not create yet. "
                          "Please check the response below: %s" % api_response))
                if api_response.status_code in [200, 201]:
                    sale_order_ids and account_move_id.write({'is_refund_move_in_ecommerce': True})
                else:
                    raise ValidationError(
                        _("Something went's to wrong. WooCommerce refund order not create yet. "
                          "Please check the response below: \n%s" % api_response.content))

        return True
