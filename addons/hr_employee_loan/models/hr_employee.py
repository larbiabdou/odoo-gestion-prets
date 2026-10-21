from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    unit_id = fields.Many2one(
        'hr.unit', "Unité", tracking=True, index=True,
        domain="[('company_id', '=', company_id)]")
    loan_ids = fields.One2many('hr.employee.loan', 'employee_id', groups="hr.group_hr_user")
    loan_count = fields.Integer(compute='_compute_loan_count', groups="hr.group_hr_user")

    def _compute_loan_count(self):
        counts = dict(self.env['hr.employee.loan']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count']))
        for employee in self:
            employee.loan_count = counts.get(employee, 0)

    def action_open_loans(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_employee_loan.action_hr_employee_loan')
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action
