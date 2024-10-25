from odoo import fields, models


class SetuSubject(models.Model):
    _name = 'setu.subject'
    _description = 'Subject'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='code')
    maximum_marks = fields.Integer(string='Maximum Marks')
    minimum_marks = fields.Integer(string='Minimum Marks')
    weightage = fields.Integer(string='Weightage')
    teacher_ids = fields.Many2many('setu.teacher', 'teacher_ids', string='Teachers')
    standard_ids = fields.Many2many('setu.standard.standard', 'standard_ids', string='Standards')
    standard_id = fields.Many2one('setu.class', string='Standard(class)')
    # student_ids=fields.One2many('setu.student','subject_student_ids',string='Student IDs')

    # subject_teacher_id=fields.Many2many('setu.teacher',string='Subject Teacher ID')#DLFKLKSDJFLKSDJFL
