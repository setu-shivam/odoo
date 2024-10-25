from odoo import fields, models, _

from odoo.exceptions import ValidationError, UserError
from dateutil import rrule
from dateutil.relativedelta import relativedelta


class SetuAcademicYear(models.Model):
    _name = 'setu.academic.year'
    _description = 'academic year'

    sequence = fields.Integer(string='sequence')
    name = fields.Char(string='name')
    code = fields.Char(string='code')
    date_start = fields.Date(string='Start Date')
    date_stop = fields.Date(string='End Date')
    month_ids = fields.One2many('setu.academic.month', 'academic_year_id', string='Months')

    def month_list(self):
        if self.date_start and self.date_stop:
            self.month_ids.unlink()
            monthline = []
            for dt in rrule.rrule(rrule.MONTHLY, dtstart=self.date_start, until=self.date_stop):
                working_days = 0
                lastday = dt + relativedelta(day=31)
                for day in rrule.rrule(rrule.DAILY, dtstart=dt, until=lastday):
                    if not (day.strftime("%a") == 'Sun' or day.strftime("%a") == 'Sat'):
                        working_days += 1
                monthline.append(
                    {"name": dt.strftime("%B"), "date_start": dt,
                     "date_stop": lastday.strftime("%Y-%m-%d"), "working_days": working_days,
                     'academic_year_id': self.id})
            self.env['setu.academic.month'].create(monthline)
        else:
            raise ValidationError(_("Select Start and End Dates"))

    def clear_list(self):
        self.month_ids.unlink()

    def unlink(self):
        for record_id in self:
            if record_id.date_start:
                raise ValidationError(_("Not Delete."))
        res = super(SetuAcademicYear, self).unlink()
        return res


class SetuAcademicMonth(models.Model):
    _name = 'setu.academic.month'
    _description = 'Academic Month'

    name = fields.Char(string='name')
    code = fields.Char(string='code')
    date_start = fields.Datetime(string='Start Date')
    date_stop = fields.Datetime(string='End Date')
    working_days = fields.Integer(string='Working Days', help='Sat-Sun Off')
    academic_year_id = fields.Many2one('setu.academic.year', string='Academic Year')
    product_id = fields.Many2one('product', string="Product")
