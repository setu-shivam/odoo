from odoo import fields, models, api
import requests
from odoo.tools.misc import split_every


class SetuEcommerceCustomerChain(models.Model):
    _inherit = 'setu.ecommerce.customer.chain'

    def process_via_import_customer_chain(self, multi_ecommerce_connector_id):
        customer_lst = []
        customer_chain_lst = []
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_process_history_obj = self.env['setu.process.history']
        setu_woocommerce_customer_chain_line_obj = self.env["setu.ecommerce.customer.chain.line"]
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        customer_api_response = woo_api_connect.get('customers', params={"per_page": 100})
        if not isinstance(customer_api_response, requests.models.Response):
            message = "Invalid Response format %s" % customer_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True
        if customer_api_response.status_code not in [200, 201]:
            message = "Invalid Request format %s" % customer_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True
        try:
            customer_api_json_data = customer_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing importing customer to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return []
        customer_lst += customer_api_json_data
        total_pages = customer_api_response.headers.get('X-WP-TotalPages')
        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                customer_lst += multi_ecommerce_connector_id.process_import_all_records(woo_api_connect,
                                                                                        multi_ecommerce_connector_id,
                                                                                        list_of_page,
                                                                                        process_history_id, model_id,
                                                                                        method='customers')
        if customer_lst:
            if len(customer_lst) > 0:
                for customer_id in split_every(125, customer_lst):
                    customer_chain_id = self.ecommerce_process_create_customer_chain(multi_ecommerce_connector_id,
                                                                                     record_created_from='import_process')
                    setu_woocommerce_customer_chain_line_obj.ecommerce_create_customer_chain_line(customer_chain_id,
                                                                                                  customer_id)
                    customer_chain_lst.append(customer_chain_id.id)
                self._cr.commit()
        return customer_chain_lst
