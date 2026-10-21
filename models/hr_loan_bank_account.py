from odoo import api, fields, models


class HrLoanBankAccount(models.Model):
    _name = 'hr.loan.bank.account'
    _description = "Compte bancaire des prêts"
    _order = 'name'

    name = fields.Char("Nom", required=True)
    bank_name = fields.Char("Banque")
    acc_number = fields.Char("N° de compte")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', "Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    initial_balance = fields.Monetary("Montant de démarrage")
    loan_ids = fields.One2many('hr.employee.loan', 'account_id', "Prêts")
    loan_count = fields.Integer("Nombre de prêts", compute='_compute_balance', store=True)
    amount_disbursed = fields.Monetary("Prêts décaissés", compute='_compute_balance', store=True)
    amount_repaid = fields.Monetary("Échéances encaissées", compute='_compute_balance', store=True)
    balance = fields.Monetary("Solde", compute='_compute_balance', store=True)

    @api.depends('initial_balance', 'loan_ids.state', 'loan_ids.amount', 'loan_ids.amount_paid')
    def _compute_balance(self):
        for account in self:
            # un prêt validé sort du compte, chaque échéance payée y revient
            loans = account.loan_ids.filtered(lambda l: l.state in ('running', 'done'))
            account.loan_count = len(account.loan_ids)
            account.amount_disbursed = sum(loans.mapped('amount'))
            account.amount_repaid = sum(loans.mapped('amount_paid'))
            account.balance = account.initial_balance - account.amount_disbursed + account.amount_repaid

    def action_open_loans(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_employee_loan.action_hr_employee_loan')
        action['domain'] = [('account_id', '=', self.id)]
        action['context'] = {'default_account_id': self.id}
        return action

    def action_open_installments(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('hr_employee_loan.action_hr_employee_loan_line')
        action['domain'] = [('account_id', '=', self.id), ('loan_state', 'in', ('running', 'done'))]
        action['context'] = {'search_default_paid': 1}
        return action
