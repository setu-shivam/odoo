from odoo import models, fields


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    def create(self, vals):
        """
        Purpose : This method is used for create stock valuation line
                when validate picking
        :param vals:
        :return:
        """
        layers = super(StockValuationLayer, self).create(vals)
        context = self._context.copy() or {}
        history_date = context.get('history_order_date', False)
        if context.get('history_order', False) and history_date and layers:
            layer_str = ",".join(map(str, layers.ids))
            self._cr.execute("""update stock_valuation_layer set create_date='%s'::date where id in (%s)""" % (
            history_date, layer_str))
            self._cr.commit()
        return layers
