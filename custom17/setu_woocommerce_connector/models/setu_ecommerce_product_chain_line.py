from odoo import fields, models, api, _


class SetuEcommerceProductChainLine(models.Model):
    _inherit = 'setu.ecommerce.product.chain.line'

    def woocommerce_connector_auto_process_ecommerce_product_chain_line(self):
        product_chain_lst = []
        setu_woocommerce_product_chain_obj = self.env["setu.ecommerce.product.chain"]

        query = """select pc.id from setu_ecommerce_product_chain_line as pcl inner join setu_ecommerce_product_chain 
        as pc on pcl.setu_ecommerce_product_chain_id = pc.id  where pcl.state='draft' and pc.is_action_require = 'False'
         ORDER BY pcl.create_date ASC"""
        self._cr.execute(query)
        product_chain_list_lst = self._cr.fetchall()
        if not product_chain_list_lst:
            return True

        for result in product_chain_list_lst:
            if result[0] not in product_chain_lst:
                product_chain_lst.append(result[0])

        product_chain_ids = setu_woocommerce_product_chain_obj.browse(product_chain_lst)
        self.initialize_ecommerce_process_product_chain_line(product_chain_ids)
        return True

    def woocommerce_connector_process_product_chain_line(self):
        setu_woocommerce_product_template_obj = self.env["setu.woocommerce.product.template"]
        setu_process_history_obj = self.env['setu.process.history']

        model_id = setu_process_history_obj.process_history_line_ids.get_model_id(
            setu_woocommerce_product_template_obj._name)
        product_chain_id = self.setu_ecommerce_product_chain_id if len(
            self.setu_ecommerce_product_chain_id) == 1 else False

        if product_chain_id:
            multi_ecommerce_connector_id = product_chain_id.multi_ecommerce_connector_id
            if not multi_ecommerce_connector_id.active:
                return True

            if product_chain_id.process_history_id:
                process_history_id = product_chain_id.process_history_id
            else:
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                                 multi_ecommerce_connector_id,
                                                                                                 model_id)

            self.env.cr.execute(
                """update setu_ecommerce_product_chain set is_chain_in_process = False where is_chain_in_process = True""")
            self._cr.commit()
            commit_count = 0
            for product_chain_line_id in self:
                commit_count += 1
                if commit_count == 10:
                    product_chain_id.is_chain_in_process = True
                    self._cr.commit()
                    commit_count = 0
                setu_woocommerce_product_template_obj.fetch_and_create_woocommerce_product(product_chain_line_id,
                                                                                           product_chain_id.multi_ecommerce_connector_id,
                                                                                           process_history_id,
                                                                                           product_chain_id.is_skip_existing_product_update)
                product_chain_id.is_chain_in_process = False
            product_chain_id.process_history_id = process_history_id

            if product_chain_id.process_history_id and not product_chain_id.process_history_id.process_history_line_ids:
                product_chain_id.process_history_id.unlink()
        return True
