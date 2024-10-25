# -*- coding: utf-8 -*-
from odoo import models


class SetuAutoDeleteProcess(models.AbstractModel):
    _name = 'setu.auto.delete.process'
    _description = "Auto Delete Process"

    def auto_delete_process(self, table_lst=[], is_delete_chain_process=False):
        if table_lst:
            try:
                table_lst += ["setu_process_history", "setu_ecommerce_order_chain", "setu_ecommerce_customer_chain",
                              "setu_ecommerce_product_chain"]
                list_table_ids = list(set(table_lst))
                for table_id in list_table_ids:
                    if is_delete_chain_process:
                        self._cr.execute("""delete from %s """ % str(table_id))
                        continue
                    self._cr.execute(
                        """delete from %s where cast(create_date as Date) <= current_date - %d""" % (str(table_id), 7))
            except Exception as error:
                return error
        return True
