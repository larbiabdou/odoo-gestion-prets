def migrate(cr, version):
    """Prêts déjà validés : la date de demande sert de date d'attribution."""
    cr.execute("""
        UPDATE hr_employee_loan
           SET date_granted = date
         WHERE date_granted IS NULL
           AND state IN ('running', 'done')
    """)
