from odoo import fields, models


class RepairRequestsServices(models.Model):
    _name = 'repair.requests.services'
    _description = 'Repair Services'

    name = fields.Char(string='Service Name', required=True)
