import base64

from dateutil.relativedelta import relativedelta
from num2words import num2words

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import file_open
from odoo.tools.image import image_data_uri

FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


class HrEmployeeLoan(models.Model):
    _name = 'hr.employee.loan'
    _description = "Prêt employé"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char("Référence", required=True, copy=False, readonly=True, default="Nouveau")
    employee_id = fields.Many2one('hr.employee', "Employé", required=True, tracking=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    unit_id = fields.Many2one(
        'hr.unit', "Unité", index=True, tracking=True,
        help="Unité de l'employé au moment de la validation du prêt.")
    company_id = fields.Many2one('res.company', "Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    account_id = fields.Many2one(
        'hr.loan.bank.account', "Compte bancaire", required=True, tracking=True, index=True,
        domain="[('company_id', '=', company_id)]")
    date = fields.Date("Date de demande", required=True, default=fields.Date.context_today, tracking=True)
    date_granted = fields.Date("Date d'attribution", readonly=True, copy=False, tracking=True)
    amount = fields.Monetary("Montant", required=True, tracking=True)
    installment_count = fields.Integer("Nombre de tranches", required=True, default=10, tracking=True)
    first_installment_date = fields.Date("Date de la 1re tranche", compute='_compute_first_installment_date')
    note = fields.Text("Motif")
    state = fields.Selection([
        ('draft', "Brouillon"),
        ('running', "En cours"),
        ('done', "Soldé"),
        ('refused', "Rejeté"),
        ('cancel', "Annulé"),
    ], "Statut", default='draft', required=True, copy=False, tracking=True)
    line_ids = fields.One2many('hr.employee.loan.line', 'loan_id', "Tranches", copy=False)
    amount_paid = fields.Monetary("Montant remboursé", compute='_compute_amounts', store=True)
    amount_residual = fields.Monetary("Reste à payer", compute='_compute_amounts', store=True)

    _amount_positive = models.Constraint('CHECK(amount > 0)', "Le montant du prêt doit être positif.")
    _installment_count_positive = models.Constraint(
        'CHECK(installment_count > 0)', "Le nombre de tranches doit être positif.")

    @api.depends('amount', 'line_ids.amount', 'line_ids.state')
    def _compute_amounts(self):
        for loan in self:
            paid = sum(loan.line_ids.filtered(lambda l: l.state == 'paid').mapped('amount'))
            loan.amount_paid = paid
            loan.amount_residual = loan.amount - paid

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.state == 'draft':
            self.unit_id = self.employee_id.unit_id

    @api.depends('date_granted')
    def _compute_first_installment_date(self):
        # 1re échéance : le 30 du mois d'attribution (dernier jour du mois en février)
        today = fields.Date.context_today(self)
        for loan in self:
            loan.first_installment_date = (loan.date_granted or today) + relativedelta(day=30)

    def _get_installment_date(self, index):
        self.ensure_one()
        return self.first_installment_date + relativedelta(months=index, day=30)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and 'unit_id' not in vals:
                vals['unit_id'] = self.env['hr.employee'].browse(vals['employee_id']).unit_id.id
            if vals.get('name', "Nouveau") == "Nouveau":
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.loan') or "Nouveau"
        return super().create(vals_list)

    def action_compute_installments(self):
        for loan in self:
            if loan.state != 'draft':
                raise UserError("Les tranches ne peuvent être recalculées que sur un prêt en brouillon.")
            currency = loan.currency_id
            base = currency.round(loan.amount / loan.installment_count)
            commands = [fields.Command.clear()]
            for i in range(loan.installment_count):
                is_last = i == loan.installment_count - 1
                commands.append(fields.Command.create({
                    'sequence': i + 1,
                    'date': loan._get_installment_date(i),
                    # la dernière tranche absorbe l'écart d'arrondi
                    'amount': currency.round(loan.amount - base * i) if is_last else base,
                }))
            loan.line_ids = commands

    def action_confirm(self):
        for loan in self:
            if not loan.line_ids:
                loan.action_compute_installments()
            total = sum(loan.line_ids.mapped('amount'))
            if loan.currency_id.compare_amounts(total, loan.amount) != 0:
                raise ValidationError(
                    "Le total des tranches (%s) ne correspond pas au montant du prêt (%s)." % (total, loan.amount))
            loan.date_granted = fields.Date.context_today(loan)
            # l'unité est figée à la validation : un changement d'unité ultérieur de l'employé ne la modifie pas
            loan.unit_id = loan.employee_id.unit_id
            # l'échéancier part du mois d'attribution
            for index, line in enumerate(loan.line_ids.sorted(lambda l: (l.sequence, l.date, l.id))):
                line.date = loan._get_installment_date(index)
        self.state = 'running'

    def action_refuse(self):
        if any(loan.state != 'draft' for loan in self):
            raise UserError("Seuls les prêts en brouillon peuvent être rejetés.")
        self.state = 'refused'

    def action_cancel(self):
        if any(line.state == 'paid' for line in self.line_ids):
            raise UserError("Impossible d'annuler un prêt dont des tranches sont déjà payées.")
        self.state = 'cancel'

    def action_draft(self):
        if any(line.state == 'paid' for line in self.line_ids):
            raise UserError("Impossible de remettre en brouillon un prêt dont des tranches sont déjà payées.")
        self.write({'state': 'draft', 'date_granted': False})

    def _update_done_state(self):
        for loan in self:
            if loan.state == 'running' and all(line.state == 'paid' for line in loan.line_ids):
                loan.state = 'done'
            elif loan.state == 'done' and any(line.state != 'paid' for line in loan.line_ids):
                loan.state = 'running'

    # --- Contrat de prêt (rapport PDF) ---

    def action_print_contract(self):
        return self.env.ref('hr_employee_loan.action_report_loan_contract').report_action(self, config=False)

    def _contract_number(self):
        self.ensure_one()
        return self.name

    def _contract_logo(self):
        with file_open('hr_employee_loan/static/img/logo_gica.jpg', 'rb') as f:
            return image_data_uri(base64.b64encode(f.read()))

    @api.model
    def _contract_format_amount(self, amount):
        # 500000.5 -> "500 000,50" (espace insécable : le montant n'est jamais coupé en fin de ligne)
        return "{:,.2f}".format(amount).replace(',', ' ').replace('.', ',')

    @api.model
    def _contract_amount_in_words(self, amount):
        dinars = int(amount)
        centimes = round((amount - dinars) * 100)
        words = "%s dinars" % num2words(dinars, lang='fr')
        if centimes:
            words += " et %s centimes" % num2words(centimes, lang='fr')
        return words[:1].upper() + words[1:]

    def _contract_installment_amount(self):
        self.ensure_one()
        first = self.line_ids.sorted('sequence')[:1]
        return first.amount if first else self.amount / (self.installment_count or 1)

    def _contract_start_month(self):
        self.ensure_one()
        first = self.line_ids.sorted('sequence')[:1]
        start = first.date if first else self.first_installment_date
        return "%s %s" % (FRENCH_MONTHS[start.month - 1], start.year)

    def _contract_employee_address(self):
        self.ensure_one()
        employee = self.employee_id.sudo()
        return ", ".join(filter(None, [employee.private_street, employee.private_city]))

    @api.model
    def get_dashboard_data(self, filters=None):
        """KPI du tableau de bord, calculés sur les prêts accordés (en cours ou soldés)."""
        filters = filters or {}
        domain = [('state', 'in', ('running', 'done'))]
        if filters.get('unit_id'):
            domain.append(('unit_id', '=', int(filters['unit_id'])))
        if filters.get('account_id'):
            domain.append(('account_id', '=', int(filters['account_id'])))
        if filters.get('date_from'):
            domain.append(('date_granted', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date_granted', '<=', filters['date_to']))
        loans = self.search(domain)

        def kpis(records):
            granted = sum(records.mapped('amount'))
            repaid = sum(records.mapped('amount_paid'))
            return {
                'count': len(records),
                'amount_granted': granted,
                'amount_repaid': repaid,
                'amount_residual': granted - repaid,
                'beneficiary_count': len(records.employee_id),
                'repayment_rate': repaid / granted if granted else 0.0,
            }

        by_unit = [
            {'unit_id': unit.id, 'name': unit.name, **kpis(loans.filtered(lambda l: l.unit_id == unit))}
            for unit in loans.unit_id.sorted('name')
        ]
        no_unit = loans.filtered(lambda l: not l.unit_id)
        if no_unit:
            by_unit.append({'unit_id': False, 'name': "Sans unité", **kpis(no_unit)})

        return {
            **kpis(loans),
            'by_unit': by_unit,
            'currency_id': self.env.company.currency_id.id,
            'loan_domain': domain,
            'line_domain': [('loan_id', 'in', loans.ids)],
            'employee_ids': loans.employee_id.ids,
            'units': self.env['hr.unit'].search_read([], ['name']),
            'accounts': self.env['hr.loan.bank.account'].search_read([], ['name']),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_not_draft(self):
        if any(loan.state not in ('draft', 'refused', 'cancel') for loan in self):
            raise UserError("Seuls les prêts en brouillon, rejetés ou annulés peuvent être supprimés.")


class HrEmployeeLoanLine(models.Model):
    _name = 'hr.employee.loan.line'
    _description = "Tranche de prêt employé"
    _order = 'loan_id, sequence, date'
    _rec_name = 'loan_id'

    loan_id = fields.Many2one('hr.employee.loan', "Prêt", required=True, ondelete='cascade', index=True)
    sequence = fields.Integer("N°")
    employee_id = fields.Many2one(related='loan_id.employee_id', store=True)
    account_id = fields.Many2one(related='loan_id.account_id', store=True)
    unit_id = fields.Many2one(related='loan_id.unit_id', store=True, index=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    loan_state = fields.Selection(related='loan_id.state', string="Statut du prêt")
    date = fields.Date("Échéance", required=True)
    amount = fields.Monetary("Montant", required=True)
    state = fields.Selection([('unpaid', "À payer"), ('paid', "Payée")], "Statut", default='unpaid', required=True)
    payment_date = fields.Date("Date de paiement")
    payment_ref = fields.Char("Référence paiement")

    def action_pay(self):
        if any(line.loan_id.state != 'running' for line in self):
            raise UserError("Seules les tranches d'un prêt en cours peuvent être payées.")
        to_pay = self.filtered(lambda l: l.state == 'unpaid')
        if not to_pay:
            return
        today = fields.Date.context_today(self)
        for line in to_pay:
            line.write({'state': 'paid', 'payment_date': line.payment_date or today})
        for loan in to_pay.loan_id:
            paid_lines = to_pay.filtered(lambda l: l.loan_id == loan)
            loan.message_post(body="Tranche(s) payée(s) : %s" % ", ".join(
                "n°%s (%s)" % (line.sequence, line.amount) for line in paid_lines))
        to_pay.loan_id._update_done_state()

    @api.model
    def _cron_pay_due_installments(self):
        """Paie automatiquement les tranches arrivées à échéance (le 30 du mois, ou le dernier jour de février).

        Lancé chaque jour : rattrape aussi les échéances passées si le serveur était arrêté ce jour-là.
        """
        lines = self.search([
            ('state', '=', 'unpaid'),
            ('loan_id.state', '=', 'running'),
            ('date', '<=', fields.Date.context_today(self)),
        ])
        for line in lines.filtered(lambda l: not l.payment_date):
            line.payment_date = line.date
        lines.filtered(lambda l: not l.payment_ref).payment_ref = "Paiement automatique"
        lines.action_pay()

    def action_unpay(self):
        if any(line.loan_id.state not in ('running', 'done') for line in self):
            raise UserError("Action impossible sur ce prêt.")
        self.write({'state': 'unpaid', 'payment_date': False})
        self.loan_id._update_done_state()
