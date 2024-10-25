from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, time
from pytz import UTC


class ProjectTask(models.Model):
    _inherit = 'project.task'

    setu_task_reference = fields.Char(string="Task Reference")
    setu_git_branch = fields.Char(string="Git Branch")
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')
    ], default='0', index=True, string="Priority", tracking=True)
    setu_meeting_hours = fields.Float(string="Meeting Hours")
    date_deadline = fields.Datetime(string='Deadline', index=True, tracking=True,
                                    default=datetime.utcnow().strftime('%Y-%m-%d 12:30'))
    config_percentage = fields.Float(string="Extra Time Percentage")
    is_overtime = fields.Boolean(readonly=True, default=False)
    estimated_hours = fields.Float(string='Estimated Time', tracking=True)

    @api.depends('effective_hours', 'subtask_effective_hours', 'allocated_hours')
    def _compute_progress_hours(self):
        res = super(ProjectTask, self)._compute_progress_hours()
        for task_id in self:
            is_overtime = False
            extra_allocated_time = float(
                self.env['ir.config_parameter'].sudo().get_param('project_task.extra_time_percentage')) + 100
            if float(task_id.progress) > extra_allocated_time:
                is_overtime = True
            task_id.is_overtime = is_overtime
        return res

    def _compute_display_name(self):
        res = super(ProjectTask, self)._compute_display_name()
        for record in self:
            record.display_name = "New"
            if record.id:
                record.display_name = "[{}] {}".format(record.id, record.name)
        return res

    def create(self, vals):
        task = super(ProjectTask, self).create(vals)
        meeting_id = self.env.ref('project_extended.project_project_meeting')
        task.config_percentage = float(
            self.env['ir.config_parameter'].sudo().get_param('project_task.extra_time_percentage'))
        if task.project_id and task.project_id.id == meeting_id.id:
            setu_meeting_hour = vals.get('setu_meeting_hours') or task.setu_meeting_hours
            existing_timesheets = self.env['account.analytic.line'].search([('task_id', '=', task.id)])
            if not existing_timesheets:
                timesheets_to_create = []
                for user in task.user_ids:
                    timesheet_vals = {
                        'employee_id': user.employee_id.id,
                        'unit_amount': setu_meeting_hour,
                        'name': 'Internal Meeting',
                        'task_id': task.id,
                    }
                    timesheets_to_create.append(timesheet_vals)
                self.env['account.analytic.line'].create(timesheets_to_create)
        return task

    def write(self, vals):
        stage_id = vals.get('stage_id')
        estimated_hours = vals.get('estimated_hours')
        current_estimated_hours = self.estimated_hours
        if stage_id and (not estimated_hours and not current_estimated_hours):
            task_stage_id = self.env['project.task.type'].browse(stage_id)
            if task_stage_id.is_estimated_hours_require:
                raise ValidationError("You can not move task to this stage. Please assign Estimate Time first !!!")

        if vals.get('description') and self.description:
            self.message_post(body_is_html=True,
                              body=_(
                                  f'Task Updated Content :{vals.get("description")}<hr>Task Old Content: {self.description}'))

        meeting_id = self.env.ref('project_extended.project_project_meeting')
        old_project_id = self.project_id
        new_project_id = vals.get('project_id')
        if old_project_id.id == meeting_id.id and old_project_id != new_project_id:
            for task in self:
                task.timesheet_ids.unlink()

        res = super(ProjectTask, self).write(vals)

        vals.update({'config_percentage': float(
            self.env['ir.config_parameter'].sudo().get_param('project_task.extra_time_percentage'))})
        for task in self:
            new_project = task.project_id
            existing_timesheets = task.timesheet_ids
            if new_project.id == meeting_id.id:
                existing_timesheets.update({'unit_amount': task.setu_meeting_hours})
                for user in task.user_ids:
                    if user.employee_id not in existing_timesheets.mapped('employee_id'):
                        timesheet_vals = {
                            'employee_id': user.employee_id.id,
                            'unit_amount': task.setu_meeting_hours or vals.get('setu_meeting_hours'),
                            'name': 'Internal Meeting',
                            'task_id': task.id,
                        }
                        self.env['account.analytic.line'].create(timesheet_vals)
                for timesheet in existing_timesheets:
                    if timesheet.employee_id.user_id not in task.user_ids:
                        timesheet.unlink()
            project_task_type = self.env['project.task.type'].browse(task.stage_id.id)
            if project_task_type.is_final_stage:
                if not task.date_deadline:
                    raise ValidationError(
                        f"You cannot move task to {project_task_type.name}.\n\nPlease assign Deadline first.")
        return res

    def action_view_timesheet(self):
        """
        added by: Riken Mashru | On : June-25-2024 | Task: 415 - Put one button inside task as Timesheet
        use : timesheets will be displayed in list view of current task and its sub-tasks
        """
        view_id = self.env.ref('hr_timesheet.timesheet_view_tree_user').id
        child_timesheet_ids = self.child_ids.timesheet_ids.ids
        parent_timesheet_ids = self.timesheet_ids.ids
        timesheet_ids = child_timesheet_ids + parent_timesheet_ids

        action = self.env["ir.actions.actions"]._for_xml_id("hr_timesheet.timesheet_action_all")
        action.update({
            'name': _('Timesheet'),
            'view_mode': 'tree,form',
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', timesheet_ids)],
        })

        return action
