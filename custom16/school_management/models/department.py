from odoo import fields, models


class Department(models.Model):
    _name = 'department'
    _description = 'Department'

    # name = fields.Char(string='Name', required=True)
    name=fields.Selection(selection=[('sports','Sportssss'),('science','Scienceeee')],string='Name')
    hod_id=fields.Many2one('teacher',string='hod')
    members_ids=fields.One2many('teacher','department_id',string='Dept. Members')