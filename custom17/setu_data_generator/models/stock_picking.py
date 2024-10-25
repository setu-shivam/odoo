#-*- coding: utf-8 -*-

from odoo import models, fields, api, _
import random
from datetime import timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

                Normally that happens when the button "Done" is pressed on a Picking view.
                @return: True
                """
        if not self._context.get('history_order', False):
            return super(StockPicking, self).action_done()

        self._check_company()

        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        delivery_gap = self.env['ir.config_parameter'].sudo(). \
            get_param('setu_data_generator.sale_delivery_gap')
        delivery_gap = int(delivery_gap)
        day = random.randint(0, delivery_gap + 1)
        delivery_date = False
        for pick in self:
            order = pick.sale_id or pick.purchase_id
            delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
            # pick.scheduled_date = delivery_date
            if pick.owner_id:
                pick.move_lines.write({'restrict_partner_id': pick.owner_id.id})
                pick.move_line_ids.write({'owner_id': pick.owner_id.id})

            # # Explode manually added packages
            # for ops in pick.move_line_ids.filtered(lambda x: not x.move_id and not x.product_id):
            #     for quant in ops.package_id.quant_ids: #Or use get_content for multiple levels
            #         self.move_line_ids.create({'product_id': quant.product_id.id,
            #                                    'package_id': quant.package_id.id,
            #                                    'result_package_id': ops.result_package_id,
            #                                    'lot_id': quant.lot_id.id,
            #                                    'owner_id': quant.owner_id.id,
            #                                    'product_uom_id': quant.product_id.uom_id.id,
            #                                    'product_qty': quant.qty,
            #                                    'qty_done': quant.qty,
            #                                    'location_id': quant.location_id.id, # Could be ops too
            #                                    'location_dest_id': ops.location_dest_id.id,
            #                                    'picking_id': pick.id
            #                                    }) # Might change first element
            # # Link existing moves or add moves when no one is related
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                # Search move with this product
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                moves = sorted(moves, key=lambda m: m.quantity < m.product_qty, reverse=True)
                if moves:
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                                                    'name': _('New Move:') + ops.product_id.display_name,
                                                    'product_id': ops.product_id.id,
                                                    'product_uom_qty': ops.qty_done,
                                                    'product_uom': ops.product_uom_id.id,
                                                    'description_picking': ops.description_picking,
                                                    'location_id': pick.location_id.id,
                                                    'location_dest_id': pick.location_dest_id.id,
                                                    'picking_id': pick.id,
                                                    'picking_type_id': pick.picking_type_id.id,
                                                    'restrict_partner_id': pick.owner_id.id,
                                                    'company_id': pick.company_id.id,
                                                    'scheduled_date' : delivery_date,
                                                    'date': delivery_date
                                                   })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
                    #'qty_done': ops.qty_done})
        if delivery_date:
            todo_moves.write({'date': delivery_date})
            todo_moves.move_line_ids.write({'date': delivery_date})
        context = self._context.copy() or {}
        delivery_date and context.update({'history_order_date': delivery_date})
        todo_moves.with_context(context)._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        if delivery_date:
            self.write({'date_done': delivery_date})
            layers = self.env['stock.valuation.layer'].sudo().search([('stock_move_id', 'in', todo_moves.ids)])
            if layers:
                layer_str = ",".join(map(str, layers.ids))
                self._cr.execute("""update stock_valuation_layer set create_date='%s'::date where id in (%s)""" % (
                delivery_date, layer_str))
                self._cr.commit()

        self._send_confirmation_email()
        return True