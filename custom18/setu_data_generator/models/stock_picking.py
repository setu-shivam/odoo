# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _set_auto_lot(self):
        """
            Allows to be called either by button or through code
        """
        lines = self.mapped("move_line_ids").filtered(
            lambda x: (not x.lot_id and not x.lot_name and x.product_id.tracking != "none")
        )
        lines.set_lot_auto()

    def _action_done(self):
        self._set_auto_lot()
        return super()._action_done()

    def button_validate(self):
        self._set_auto_lot()
        return super().button_validate()
