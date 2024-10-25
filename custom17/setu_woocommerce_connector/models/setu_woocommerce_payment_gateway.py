from odoo import fields, models, api


class SetuWooCommercePaymentGateway(models.Model):
    _name = 'setu.woocommerce.payment.gateway'
    _description = 'WooCommerce Payment Gateway'

    active = fields.Boolean(string="Active GateWay", default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string="Code", required=True, translate=True)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', required=True)

    _sql_constraints = [
        ('payment_gateway_uniq', 'unique (code,multi_ecommerce_connector_id)', 'Payment Method code must be unique!!')]

    def create_or_update_woocommerce_payment_gateway(self, multi_ecommerce_connector_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_process_history_obj = self.env['setu.process.history']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        setu_process_history_id = setu_process_history_obj.create_woocommerce_process_history(
            history_perform="import",
            multi_ecommerce_connector_id=multi_ecommerce_connector_id,
            model_id=model_id)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        payment_api_response = woo_api_connect.get("payment_gateways")
        if payment_api_response.status_code not in [200, 201]:
            message = payment_api_response.content
            if message:
                setu_process_history_line_obj.woocommerce_common_process_log(message, model_id, setu_process_history_id)
                return False
        payment_data_json = payment_api_response.json()
        for payment_data in payment_data_json:
            if payment_data.get('enabled'):
                name = payment_data.get('title')
                code = payment_data.get('id')
                existing_payment_ids = self.search(
                    [('code', '=', code),
                     ('multi_ecommerce_connector_id', '=',
                      multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)]).ids
                if existing_payment_ids or not name or not code:
                    continue
                self.create(
                    {'name': name, 'code': code,
                     'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
        if not setu_process_history_id.process_history_line_ids:
            setu_process_history_id.sudo().unlink()
        return True
