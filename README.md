# Gestion des prêts au personnel (Odoo 19)

Module Odoo 19 `hr_employee_loan` : gestion simple des prêts accordés aux employés, sans paie ni comptabilité.

## Fonctionnalités

- **Prêts** : date de demande, date d'attribution (remplie à la validation), montant, nombre d'échéances (10 par défaut), rejet, annulation.
- **Échéancier** : générée automatiquement, 1re échéance le 30 du mois d'attribution (dernier jour du mois en février), puis le 30 de chaque mois.
- **Paiement des échéances** : manuel (une par une ou en masse) ou automatique par une action planifiée quotidienne qui paie les échéances échues.
- **Comptes bancaires** : montant de démarrage et solde (= démarrage − prêts validés + échéances payées).
- **Unités** : unité de l'employé, figée sur le prêt au moment de la validation.
- **Tableau de bord** : prêts accordés, montant accordé, remboursé, reste à recouvrer, bénéficiaires, taux de remboursement, avec filtres et détail par unité.
- **Contrat de prêt** imprimable en PDF depuis le prêt.
- **Menu principal « Gestion des prêts »** avec une fiche employé simplifiée (téléphone, fonction, adresse, unité, département).

## Installation

1. Ajouter le dossier `addons` au `addons_path` d'Odoo 19 (voir `odoo.conf.example`).
2. Mettre à jour la liste des applications puis installer **Prêts au personnel**.

Dépendances : `hr`, `mail` (et la bibliothèque Python `num2words`, fournie avec Odoo).

## Lancement (Windows)

Copier `odoo.conf.example` en `odoo.conf`, l'adapter, puis lancer `lancer.bat`.
