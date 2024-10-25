from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        setu_return_order_obj = self.env['setu.return.order'].sudo()
        if 'state' in vals and self:
            if self[0].picking_code == 'incoming' and vals.get('state') == 'done':
                return_order_id = setu_return_order_obj.search([('return_picking_id', '=', self[0].picking_id.id)])
                return_order_id and return_order_id.state == 'approve'
        return super(StockMove, self).write(vals)
