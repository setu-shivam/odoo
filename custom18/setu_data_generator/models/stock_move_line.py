from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move.line'

    def _prepare_auto_lot_values(self):
        """
            Prepare multi valued lots per line to use multi creation.
        """
        self.ensure_one()
        return {"product_id": self.product_id.id, "company_id": self.company_id.id}

    def set_lot_auto(self):
        """
            Create lots using create_multi to avoid too much queries
            As move lines were created by product or by tracked 'serial'
            products, we apply the lot with both different approaches.
        """
        values = []
        stock_lot_obj = self.env["stock.lot"]
        lots_by_product = dict()
        for line in self:
            values.append(line._prepare_auto_lot_values())
        lots = stock_lot_obj.create(values)
        for lot in lots:
            if lot.product_id.id not in lots_by_product:
                lots_by_product[lot.product_id.id] = lot
            else:
                lots_by_product[lot.product_id.id] += lot
        i = 0
        for line in self:
            if len(lots) > i:
                line.lot_id = lots[i].id
                i += 1
