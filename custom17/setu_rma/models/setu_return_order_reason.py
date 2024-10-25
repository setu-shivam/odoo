from odoo import fields, models, api, _


class SetuReturnOrderReason(models.Model):
    _name = 'setu.return.order.reason'
    _description = 'Return Order Reason'

    name = fields.Char(string="RMA Reason")
    action = fields.Selection(
        [('refund', 'Refund'), ('replace', 'Replace'), ('repair', 'Repair'), ('buyback', 'BuyBack')],
        string="Related Action")
