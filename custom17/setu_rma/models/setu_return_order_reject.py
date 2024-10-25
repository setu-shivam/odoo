from odoo import fields, models, api, _


class SetuReturnOrderReject(models.Model):
    _name = 'setu.return.order.reject'
    _description = 'Return Order Reject'

    name = fields.Char(string="Return Order Reject")
