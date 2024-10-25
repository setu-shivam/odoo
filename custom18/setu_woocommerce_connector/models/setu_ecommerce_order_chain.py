from odoo import fields, models, api
import pytz
from datetime import timedelta


class SetuEcommerceOrderChain(models.Model):
    _inherit = 'setu.ecommerce.order.chain'

    def process_to_import_all_woocommerce_order(self, multi_ecommerce_connector_id, from_date="", to_date=""):
        order_chain_lst = []
        from_date = from_date if from_date else multi_ecommerce_connector_id.woocommerce_last_order_import_date - timedelta(
            days=1) if multi_ecommerce_connector_id.last_order_import_date else fields.Datetime.now() - timedelta(
            days=1)
        to_date = to_date if to_date else fields.Datetime.now()
        from_date = pytz.utc.localize(from_date).astimezone(
            pytz.timezone(multi_ecommerce_connector_id.woocommerce_store_timezone)) if from_date else False
        to_date = pytz.utc.localize(to_date).astimezone(
            pytz.timezone(multi_ecommerce_connector_id.woocommerce_store_timezone))
        parameter = {"after": str(from_date)[:19], "before": str(to_date)[:19], "per_page": 100, "page": 1,
                     "order": "asc"}
        orders_data = self.process_to_fetch_all_orders(parameter, multi_ecommerce_connector_id)
        multi_ecommerce_connector_id.woocommerce_last_order_import_date = to_date.astimezone(
            pytz.timezone("UTC")).replace(tzinfo=None)
        if not orders_data:
            return []
        order_chain_id = self.ecommerce_process_create_order_chain(multi_ecommerce_connector_id, orders_data,
                                                                   'import_process')
        order_chain_lst.append(order_chain_id.id)
        return order_chain_lst

    @api.model
    def process_to_fetch_all_orders(self, parameter, multi_ecommerce_connector_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_process_history_obj = self.env['setu.process.history']
        status = ",".join(map(str, multi_ecommerce_connector_id.setu_woocommerce_order_status_ids.mapped("status")))
        parameter["status"] = status
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        try:
            order_api_response = woo_api_connect.get("orders", params=parameter)
        except Exception as e:
            message = "Requested resource doesn't exist or missing requested information on WooCommerce store. %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if order_api_response.status_code != 200:
            message = "Invalid Request Format %s" % (str(order_api_response.content))
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        order_data_json_lst = order_api_response.json()
        total_pages = order_api_response.headers.get("X-WP-TotalPages")
        if int(total_pages) > 1:
            for page in range(2, int(total_pages) + 1):
                parameter["page"] = page
                order_api_response = woo_api_connect.get("orders", params=parameter)
                order_data_json_lst += order_api_response.json()

        return order_data_json_lst

    def woocommerce_connector_import_ecommerce_order_chain(self, multi_ecommerce_connector_id):
        from_date = multi_ecommerce_connector_id.woocommerce_last_order_import_date - timedelta(
            days=1) if multi_ecommerce_connector_id.woocommerce_last_order_import_date else fields.Datetime.now() - timedelta(
            days=1)
        to_date = fields.Datetime.now()
        self.process_to_import_all_woocommerce_order(multi_ecommerce_connector_id, from_date, to_date)
        return True
