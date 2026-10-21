{
    'name': 'Prêts au personnel',
    'version': '19.0.1.6.0',
    'category': 'Human Resources',
    'summary': "Prêts aux employés : comptes bancaires, échéancier et paiement des tranches",
    'author': 'Custom',
    'depends':['hr', 'mail'],
    'data': [
        'security/hr_employee_loan_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_employee_loan_views.xml',
        'views/hr_loan_bank_account_views.xml',
        'views/hr_unit_views.xml',
        'views/hr_employee_views.xml',
        'views/menus.xml',
        'report/hr_employee_loan_contract.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_employee_loan/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
