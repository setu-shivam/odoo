# -*- coding: utf-8 -*-
from odoo import fields, models


class Teacher(models.Model):
    _name = 'teacher'
    _description = 'Teacher'
    # _rec_name = 'code'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='code', required=True)
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Gender')
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    subject = fields.Char(string='Subject', required=True)
    city_id = fields.Many2one('city',string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    department_id = fields.Many2one('department', string='Department')
    hod=fields.Boolean(string='Hod')
    student_ids = fields.One2many('student', 'classteacher_id', string='Class Students')

