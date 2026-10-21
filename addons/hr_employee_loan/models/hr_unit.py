from odoo import fields, models


class HrUnit(models.Model):
    _name = 'hr.unit'
    _description = "Unité"
    _order = 'name'

    name = fields.Char("Nom", required=True)
    code = fields.Char("Code")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', "Société", required=True, default=lambda self: self.env.company)
    employee_ids = fields.One2many('hr.employee', 'unit_id', "Employés")

    _name_company_uniq = models.Constraint(
        'unique (name, company_id)', "Une unité portant ce nom existe déjà dans cette société.")
