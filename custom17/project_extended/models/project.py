from datetime import date
from odoo.exceptions import UserError, ValidationError, AccessError
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import date, timedelta


class Task(models.Model):
    _inherit = "project.task"

    # @api.depends('name')
    # def _compute_display_name(self):
    #     for rec in self:
    #         rec.display_name = "[{}] {}".format(rec.id, rec.name)

    def name_get(self):
        return [(task.id, task._build_display_name()) for task in self]

    def _build_display_name(self):
        self.ensure_one()
        display_name = f"[{self.id}] {self.name}"
        return display_name

    @property
    def SELF_WRITABLE_FIELDS(self):
        return super().SELF_WRITABLE_FIELDS.union({'description'})

    # override to not check access for
    def _ensure_fields_are_accessible(self, fields, operation='read', check_group_user=True):
        assert operation in ('read', 'write'), 'Invalid operation'
        if fields and (not check_group_user or self.env.user.has_group('base.group_portal')) and not self.env.su:
            unauthorized_fields = set(fields) - (
                self.SELF_READABLE_FIELDS if operation == 'read' else self.SELF_WRITABLE_FIELDS)
            if unauthorized_fields:
                raise AccessError(
                    _('You cannot %s %s fields in task.', operation if operation == 'read' else '%s on' % operation,
                      ', '.join(unauthorized_fields)))


class Project(models.Model):
    _inherit = "project.project"

    def action_timesheet_current_month(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'project_extended.product_extended_action_timesheet_current_month')
        action['domain'] = [('project_id', '=', self.id),
                            ('date', '<', date.today().replace(day=1) + relativedelta(months=1)),
                            ('date', '>=', date.today().replace(day=1))]
        return action

    def action_timesheet_previous_month(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'project_extended.product_extended_action_timesheet_previous_month')
        action['domain'] = [('project_id', '=', self.id),
                            ('date', '>=', date.today().replace(day=1) - relativedelta(months=1)),
                            ('date', '<', date.today().replace(day=1))]
        return action

    def name_get(self):
        return [(project.id, project._build_display_name()) for project in self]

    def _build_display_name(self):
        self.ensure_one()
        display_name = "[{}] {}".format(self.id, self.name)
        return display_name

    # @api.depends('name')
    # def _compute_display_name(self):
    #     for rec in self:
    #         rec.display_name = "[{}] {}".format(rec.id, rec.name)
