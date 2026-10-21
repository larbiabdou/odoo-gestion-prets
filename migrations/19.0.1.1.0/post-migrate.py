from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Rattache les prêts existants à un compte bancaire par défaut par société."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    loans = env['hr.employee.loan'].with_context(active_test=False).search([('account_id', '=', False)])
    for company in loans.company_id:
        account = env['hr.loan.bank.account'].create({
            'name': "Compte principal",
            'company_id': company.id,
            'initial_balance': 0.0,
        })
        loans.filtered(lambda l: l.company_id == company).account_id = account
