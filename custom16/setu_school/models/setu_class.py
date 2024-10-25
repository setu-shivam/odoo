from odoo import fields ,models

class SetuClass(models.Model):
    _name ='setu.class'
    _description='Class'

    name=fields.Char(string='Name',required=True)
    class_teacher_id=fields.Many2one('setu.teacher',string='Class Teacher')
    teacher_ids=fields.Many2many('setu.teacher','class_ids',string='Teacher')
    student_ids=fields.One2many('setu.student','class_id',string='Students')
    school_ids=fields.Many2many('setu.school','school_ids',string='Schools')
    subject_ids=fields.Many2many('setu.subject','class_subject_ids',string='Subjects')
