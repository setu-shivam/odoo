from odoo import fields,models

class SetuGradeLine(models.Model):
    _name = 'setu.grade.line'
    _description = 'Grade Line'

    from_mark=fields.Integer(string='From Marks')
    to_mark=fields.Integer(string='To Marks')
    grade_name=fields.Char(string='Grade Name')
    fail=fields.Boolean(string='Fail')
    grade_id=fields.Many2one('setu.grade',string='Grade')