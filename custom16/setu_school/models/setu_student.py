from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class SetuStudent(models.Model):
    _name = 'setu.student'
    _description = 'Student'
    _rec_name = 'first_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    first_name = fields.Char(string='First Name', required=True)
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Gender')
    dob = fields.Datetime(string='Birthdate')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    isEligible = fields.Boolean(string='Eligible', compute='_compute_age')
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Text(string='Email')
    mobile = fields.Char(string='Mobile')
    bloodgroup = fields.Selection(
        selection=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'),
                   ('O-', 'O-')], string='Blood Group')
    weight = fields.Integer(string='Weight')
    height = fields.Integer(string='Height')
    caste_id = fields.Many2one('setu.student.caste', string='Caste')
    mother_tongue = fields.Many2one('setu.mother.tongue', string='Mothertongue')
    address = fields.Text(string='Address')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    sports_person = fields.Boolean(string='Sports Person')
    game_type = fields.Selection(selection=[('indoor', 'Indoor'), ('outdoor', 'Outdoor')], string='Game Type')
    indoor_games = fields.Selection(selection=[('chess', 'Chess'), ('carrom', 'Carrom')], string='Indoor')
    outdoor_games = fields.Selection(selection=[('cricket', 'Cricket'), ('football', 'Football')], string='Outdoor')

    terminate_reason = fields.Char(string='Terminate Reason')
    active = fields.Boolean(string='Active', default='True')
    standard_id = fields.Many2one('setu.standard.standard', string='Standard')
    division_id = fields.Many2one('setu.standard.division', string='Division')
    medium_id = fields.Many2one('setu.standard.medium', string='Medium')
    school_id = fields.Many2one('setu.school', string='School')

    admission_date = fields.Date(string='Admission Date')
    academic_year_id = fields.Many2one('setu.academic.year', string='Academic Year')
    roll_no = fields.Integer(string='Roll No.')
    class_id = fields.Many2one('setu.class', string='Class')
    class_teacher_id = fields.Many2one('setu.teacher', string='Class Teacher')
    class_teacher_email = fields.Char(string='Class Teacher Email', compute='_compute_classteacher_email')
    # alternate_id = fields.Many2one('setu.teacher', string='Alternate Teacher',compute='_compute_classteacher_alternate')
    # classteacher_email=fields.Char(related='class_teacher_id.workemail')
    alternate_teacher_id = fields.Many2one(related='class_teacher_id.alternate_id')
    teacher_ids = fields.Many2many('setu.teacher', 'student_teacher_ids', string='Teachers')
    subject_ids = fields.Many2many('setu.subject', 'student_subjects', string='Subjects')
    principal_id = fields.Many2one('setu.teacher', string='Principal')

    isEdited = fields.Boolean(string='isEdited')
    user_id = fields.Many2one("res.users", string="School User")

    # ------------------------------------------------
    # @api.model
    # def create(self, vals):
    #     rec = self.env['setu.teacher'].search(
    #         [('class_teacher', '=', 'True'), ('standard_id', '=', vals.get('standard_id')),
    #          ('medium_id', '=', vals.get('medium_id')), ('division_id', '=', vals.get('division_id'))], limit=1)
    #     vals.update({'class_teacher_id': rec.id})
    #     return super(SetuStudent, self).create(vals)

    # both works same:

    @api.model
    def create(self, vals):
        res = super(SetuStudent, self).create(vals)
        rec = self.env['setu.teacher'].search([('class_teacher', '=', 'True'), ('standard_id', '=', res.standard_id.id), ('medium_id', '=', res.medium_id.id), ('division_id', '=', res.division_id.id)], limit=1)

        res.class_teacher_id = rec.id
        return res
    # ------------------------------------------------

    def write(self, vals):
        vals.update({"isEdited": True})
        return super(SetuStudent, self).write(vals)

    # @api.constrains('first_name', 'standard_id', 'division_id', 'medium_id')
    # def check_not_null_name(self):
    #     for rec in self:
    #         if not (rec.first_name and rec.standard_id and rec.division_id and rec.medium_id):
    #             raise ValidationError("Required Details : \n\n Name,Standard,Medium,Division")

    def assign(self):
        # try :
        if self.division_id and self.medium_id and self.standard_id:
            rec = self.env['setu.teacher'].search(
                    [('class_teacher', '=', 'True'), ('standard_id', '=', self.standard_id.id),
                     ('medium_id', '=', self.medium_id.id), ('division_id', '=', self.division_id.id)], limit=1)
            self.class_teacher_id = rec.id
        # except:
        else:
            raise ValidationError("Code Already Exists")
        # finally:
        #     self.principal_id = self.school_id.principal_id

    @api.depends('class_teacher_id')
    # @api.onchange('class_teacher_id')
    def _compute_classteacher_email(self):
        for rec in self:
            if rec.class_teacher_id:
                rec.class_teacher_email = rec.class_teacher_id.workemail
            else:
                rec.class_teacher_email = False

# both work same
    # @api.onchange('class_teacher_id')
    # def _onchange_teacher_email(self):
    #     for rec in self:
    #         if rec.class_teacher_id:
    #             rec.class_teacher_email = rec.class_teacher_id.workemail
    #         else:
    #             rec.class_teacher_email = False

    # def _compute_classteacher_alternate(self):
    #     for rec in self:
    #         if rec.class_teacher_id:
    #             rec.alternate_id = rec.class_teacher_id.alternate_id
    #         else:
    #             rec.alternate_id = False

    @api.depends('dob')
    def _compute_age(self):
        for rec in self:
            if rec.dob and rec.dob <= fields.Datetime.today():
                rec.age = relativedelta(
                    fields.Date.from_string(fields.Date.today()),
                    fields.Date.from_string(rec.dob)).years
                if rec.age >= 18:
                    rec.isEligible = True
                else:
                    rec.isEligible = False
            else:
                rec.age = False
                rec.isEligible = False

    # both work same
    # @api.onchange('dob')
    # def _onchange_field(self):
    #     for rec in self:
    #         if rec.dob and rec.dob <= fields.Datetime.today():
    #             rec.age = relativedelta(
    #                 fields.Date.from_string(fields.Date.today()),
    #                 fields.Date.from_string(rec.dob)).years
    #             if rec.age >= 18:
    #                 rec.isEligible=True
    #             else:
    #                 rec.isEligible = False

    # def copy(self, default=None):
    #     default = dict(default or {})
    #     default.update(first_name= ("%s (copy)") % self.first_name)
    #     return super().copy(default)

    def copy(self, default=None):
        raise ValidationError('You Can\'t')

    @api.onchange('school_id')
    def _onchange_school_id(self):
        for rec in self:
            if rec.school_id:
                self.principal_id = self.school_id.principal_id
            else:
                rec.school_id = False

    # school = fields.Integer(string='school')
    # schoolname = fields.Char(string='School Name', compute='_compute_school')
    # @api.onchange('school')
    # def _compute_school(self):
    #     for rec in self:
    #         if rec.school:
    #             res=self.env['setu.school'].browse(rec.school).name
    #             rec.schoolname = res
    #         else:
    #             rec.schoolname = False
