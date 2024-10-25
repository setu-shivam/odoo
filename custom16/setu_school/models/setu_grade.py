from odoo import fields,models

class SetuGrade(models.Model):
    _name = 'setu.grade'
    _description = 'Grade'

    name = fields.Char(string='Name', required=True)
    grade_line_ids=fields.One2many('setu.grade.line','grade_id',string='Grade Line')
