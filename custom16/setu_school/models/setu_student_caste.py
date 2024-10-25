from odoo import fields, models


class SetuStudentCaste(models.Model):
    _name = 'setu.student.caste'
    _description = 'Student Caste'

    name = fields.Char(string='Name', required=True)
