from odoo import fields, models, api, _
from datetime import datetime
import json


class SetuEcommerceCustomerChainLine(models.Model):
    _inherit = 'setu.ecommerce.customer.chain.line'

    @api.model
    def woocommerce_connector_auto_process_ecommerce_customer_chain_line(self):
        setu_woocommerce_customer_chain_obj = self.env["setu.ecommerce.customer.chain"]
        customer_chain_lst = []

        query = """select cc.id from setu_ecommerce_customer_chain_line as ccl inner join setu_ecommerce_customer_chain 
        as cc on ccl.setu_ecommerce_customer_chain_id = cc.id where ccl.state='draft' and cc.is_action_require = 'False'
         ORDER BY ccl.create_date ASC """
        self._cr.execute(query)
        customer_data_chain_list = self._cr.fetchall()
        if not customer_data_chain_list:
            return True

        for customer_chain_id in customer_data_chain_list:
            if customer_chain_id[0] not in customer_chain_lst:
                customer_chain_lst.append(customer_chain_id[0])
        customer_chain_ids = setu_woocommerce_customer_chain_obj.browse(customer_chain_lst)
        self.initialize_ecommerce_process_customer_chain_line(customer_chain_ids)
        return True

    def woocommerce_connector_process_ecommerce_customer_chain_line(self):
        setu_process_history_obj = self.env["setu.process.history"]
        customer_chain_ids = self.mapped('setu_ecommerce_customer_chain_id')

        for customer_chain_id in customer_chain_ids:
            multi_ecommerce_connector_id = customer_chain_id.multi_ecommerce_connector_id
            if not multi_ecommerce_connector_id.active:
                return True

            if customer_chain_id.process_history_id:
                process_history_id = customer_chain_id.process_history_id
            else:
                model_id = setu_process_history_obj.process_history_line_ids.get_model_id("res.partner")
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                                 customer_chain_id.multi_ecommerce_connector_id,
                                                                                                 model_id)
                self.env.cr.execute(
                    """update setu_ecommerce_customer_chain set is_chain_in_process = False 
                    where is_chain_in_process = True""")
                self._cr.commit()

            self.create_woocommerce_res_partner(multi_ecommerce_connector_id, customer_chain_id, process_history_id)
            customer_chain_id.process_history_id = process_history_id
            if process_history_id and not process_history_id.process_history_line_ids:
                process_history_id.unlink()
        return True

    def woocommerce_connector_process_ecommerce_create_customer_chain_line(self, setu_ecommerce_customer_chain_id,
                                                                           customer_chain_lst):
        for customer_chain_data in customer_chain_lst:
            if customer_chain_data.get('billing'):
                first_name = customer_chain_data.get('billing').get('first_name')
                last_name = customer_chain_data.get('billing').get('last_name')
                name = "%s %s" % (first_name, last_name)
            else:
                name = ""
            line_vals = {"name": name.strip(),
                         "ecommerce_customer_id": customer_chain_data.get("id", False),
                         "customer_chain_line_data": json.dumps(customer_chain_data),
                         "last_customer_chain_process_date": datetime.now(),
                         "multi_ecommerce_connector_id": setu_ecommerce_customer_chain_id.multi_ecommerce_connector_id and setu_ecommerce_customer_chain_id.multi_ecommerce_connector_id.id,
                         "setu_ecommerce_customer_chain_id": setu_ecommerce_customer_chain_id and setu_ecommerce_customer_chain_id.id}
            self.create(line_vals)
        return True

    def create_woocommerce_res_partner(self, multi_ecommerce_connector_id, customer_chain_id, process_history_id):
        res_partner_obj = self.env["res.partner"]
        commit_count = 0

        for customer_chain_line_id in self:
            commit_count += 1
            if commit_count == 10:
                customer_chain_id.is_chain_in_process = True
                self._cr.commit()
                commit_count = 0

            customer_data = json.loads(customer_chain_line_id.customer_chain_line_data)
            woocommerce_main_partner_id = res_partner_obj.create_main_res_partner_woocommerce(customer_data,
                                                                                              multi_ecommerce_connector_id,
                                                                                              customer_chain_line_id,
                                                                                              process_history_id)
            if woocommerce_main_partner_id:
                if customer_data.get('billing'):
                    res_partner_obj.create_child_woocommerce_customer(customer_data.get('billing'),
                                                                      woocommerce_main_partner_id, "invoice")
                if customer_data.get('shipping'):
                    res_partner_obj.create_child_woocommerce_customer(customer_data.get('shipping'),
                                                                      woocommerce_main_partner_id, "delivery")
                customer_chain_line_id.update({"state": "done", "last_customer_chain_process_date": datetime.now()})
            else:
                customer_chain_line_id.update({"state": "fail", "last_customer_chain_process_date": datetime.now()})
            customer_chain_id.is_chain_in_process = False
