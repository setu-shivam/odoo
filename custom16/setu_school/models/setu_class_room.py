from odoo import fields,models

class SetuClassRoom(models.Model):
    _name = 'setu.class.room'
    _description = 'Class Room'

    name = fields.Char(string='Name', required=True)
    number=fields.Integer(string='Room Number')