from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_allow_child_company_journal = fields.Boolean(default=False, copy=False)
