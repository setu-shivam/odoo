from odoo import fields, models, api


class SetuWooCommerceSaleProcessConfiguration(models.Model):
    _name = 'setu.woocommerce.sale.process.configuration'
    _description = 'WooCommerce Sale Process Configuration'

    @api.model
    def _get_default_account_payment_terms(self):
        immediate_payment_terms_id = self.env.ref("account.account_payment_term_immediate")
        return immediate_payment_terms_id and immediate_payment_terms_id.id or False

    active = fields.Boolean(string="Active", default=True)

    woocommerce_financial_status = fields.Selection(
        [('paid', 'The finances have been paid'), ('not_paid', 'The finances have been not paid')], default="paid",
        required=True)
    setu_sale_order_automation_id = fields.Many2one("setu.sale.order.automation", string="WorkFlow Automation")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', required=True)
    setu_woocommerce_payment_gateway_id = fields.Many2one("setu.woocommerce.payment.gateway", string="Payment Gateway",
                                                          ondelete="restrict", required=True)
    account_payment_term_id = fields.Many2one('account.payment.term', string='Payment Term',
                                              default=_get_default_account_payment_terms)

    _sql_constraints = [('_sale_process_unique_constraint',
                         'unique(woocommerce_financial_status,multi_ecommerce_connector_id,'
                         'setu_woocommerce_payment_gateway_id)',
                         'Woocommerce Financial status must be unique')]
