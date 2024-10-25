from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    return_partner_id = fields.Many2one('res.partner', string="Return Partner ID")
