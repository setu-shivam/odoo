from odoo import fields, models, api


class SetuReturnReason(models.Model):
    _name = 'setu.return.reason'
    _description = 'Customer Return Reason'

    name = fields.Char(string="Name")

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name)",
            "Customer Return Reason name must be unique",
        ),
    ]
