from odoo import fields, models, api, _


class SetuEcommerceOrderChainLine(models.Model):
    _inherit = 'setu.ecommerce.order.chain.line'

    def woocommerce_connector_auto_process_ecommerce_order_chain_line(self):
        order_chain_lst = []
        setu_ecommerce_order_chain_obj = self.env["setu.ecommerce.order.chain"]

        self.env.cr.execute(
            """update setu_ecommerce_order_chain set is_chain_in_process = False where is_chain_in_process = True""")
        self._cr.commit()
        query = """select oc.id from setu_ecommerce_order_chain_line as ocl inner join setu_ecommerce_order_chain as oc 
        on ocl.setu_ecommerce_order_chain_id = oc.id  where ocl.state='draft' and oc.is_action_require = 'False'  
        ORDER BY ocl.create_date ASC"""
        self._cr.execute(query)
        order_chain_list = self._cr.fetchall()
        if not order_chain_list:
            return True

        for result in order_chain_list:
            if result[0] not in order_chain_lst:
                order_chain_lst.append(result[0])

        order_chain_ids = setu_ecommerce_order_chain_obj.browse(order_chain_lst)
        self.initialize_ecommerce_process_process_order_chain_line(order_chain_ids)
        return True

    def woocommerce_connector_process_order_chain_line(self, update_order=False):
        sale_order_obj = self.env["sale.order"]
        setu_process_history_obj = self.env['setu.process.history']

        order_chain_id = self.mapped('setu_ecommerce_order_chain_id') if len(
            self.mapped('setu_ecommerce_order_chain_id')) == 1 else False
        if order_chain_id:
            if not order_chain_id.multi_ecommerce_connector_id.active:
                return True

            if order_chain_id.process_history_id:
                process_history_id = order_chain_id.process_history_id
            else:
                model_id = setu_process_history_obj.process_history_line_ids.get_model_id("sale.order")
                multi_ecommerce_connector_id = order_chain_id.multi_ecommerce_connector_id
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                                 multi_ecommerce_connector_id,
                                                                                                 model_id)

            order_chain_id.is_chain_in_process = True
            if update_order:
                sale_order_obj.update_created_sale_order_via_chain_process(self, process_history_id)
            else:
                sale_order_obj.process_import_sale_order_chain_based(self, process_history_id)

            order_chain_id.is_chain_in_process = False
            order_chain_id.process_history_id = process_history_id
            if process_history_id and not process_history_id.process_history_line_ids:
                process_history_id.unlink()
        return True
