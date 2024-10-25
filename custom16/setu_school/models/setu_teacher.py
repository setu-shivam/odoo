from odoo import fields, models, api
from odoo.exceptions import ValidationError, MissingError


class SetuTeacher(models.Model):
    _name = 'setu.teacher'
    _description = 'Teachers'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    code = fields.Char(string='code', tracking=True)
    age = fields.Integer(string='age')
    dob = fields.Date(string='Birthdate')
    standard_id = fields.Many2one('setu.standard.standard', string='Standard', help='Responsibility of Academic Class')
    medium_id = fields.Many2one('setu.standard.medium', string='Medium')
    division_id = fields.Many2one('setu.standard.division', string='Division')
    subject_ids = fields.Many2many('setu.subject', string='Subject ID')
    school_id = fields.Many2one('setu.school', string='School ID')
    student_ids = fields.One2many('setu.student', 'class_teacher_id', string='Student IDs')
    class_teacher = fields.Boolean(string='Class Teacher')
    alternate_id = fields.Many2one('setu.teacher', string='Alternate')
    workphone = fields.Char(string='Work Phone', unaccent=False)
    workemail = fields.Char(string='Work Email')
    workaddress = fields.Text(string='Work Address')
    workcity = fields.Many2one('city', string='Work City')
    workstate = fields.Many2one('state', string='Work State')
    workcountry = fields.Many2one('country', string='Work Country')
    workzip = fields.Char(string='Work Zip')

    homephone = fields.Char(string='Home Phone', unaccent=False)
    homeemail = fields.Char(string='Home Email')
    homeaddress = fields.Text(string='Home Address')
    homecity = fields.Many2one('city', string='Home City')
    homestate = fields.Many2one('state', string='Home State')
    homecountry = fields.Many2one('country', string='Home Country')
    homezip = fields.Char(string='Home Zip')

    show_notebooks = fields.Boolean(string='Show Notebooks')
    show_students = fields.Boolean(string='Show Students')

    isEdited = fields.Boolean(string='isEdited', readonly=True)

    # @api.constrains('name','code','standard_id','medium_id','division_id')
    # def check_valid(self):
    #     for rec in self:
    #         if not(rec.name and rec.code and rec.standard_id and rec.medium_id and rec.division_id):
    #             raise MissingError("Required Deatils : \n\n Name,Code,Standard,Medium,Division")

    @api.constrains('code')
    def code_uniq(self):
        for rec in self:
            ext = self.search([('code', '=ilike', rec.code), ('id', '!=', rec.id)])
            if ext:
                raise ValidationError("Code Already Exists")

    def write(self, vals):
        vals.update({"isEdited": True})
        return super(SetuTeacher, self).write(vals)

    # def write(self,vals):
    #     ext_code = self.code
    #     if ext_code:
    #         vals = {"code": ext_code}
    #         raise ValidationError("code cant change")
    #     return super(SetuTeacher, self).write(vals)

    # try:
    # ext_code=self.code
    #
    # except:
    #     raise ValidationError("code cant change")
    # finally:
    #     vals={"code":ext_code}
    # return super(SetuTeacher,self).write(vals)
