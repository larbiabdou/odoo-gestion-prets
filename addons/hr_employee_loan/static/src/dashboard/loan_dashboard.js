import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary, formatPercentage } from "@web/views/fields/formatters";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class LoanDashboard extends Component {
    static props = { ...standardActionServiceProps };
    static components = { Layout };
    static template = "hr_employee_loan.LoanDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.filters = useState({ unit_id: "", account_id: "", date_from: "", date_to: "" });
        this.state = useState({ data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call("hr.employee.loan", "get_dashboard_data", [], {
            filters: { ...this.filters },
        });
    }

    onFilterChange(name, ev) {
        this.filters[name] = ev.target.value;
        this.load();
    }

    resetFilters() {
        Object.assign(this.filters, { unit_id: "", account_id: "", date_from: "", date_to: "" });
        this.load();
    }

    get cards() {
        const d = this.state.data;
        return [
            { key: "count", label: "Prêts accordés", value: d.count, icon: "fa-file-text-o", open: () => this.openLoans() },
            { key: "granted", label: "Montant total accordé", value: this.money(d.amount_granted), icon: "fa-money", open: () => this.openLoans() },
            { key: "repaid", label: "Montant total remboursé", value: this.money(d.amount_repaid), icon: "fa-check-circle", open: () => this.openLines("paid") },
            { key: "residual", label: "Reste à recouvrer", value: this.money(d.amount_residual), icon: "fa-hourglass-half", open: () => this.openLines("unpaid") },
            { key: "beneficiaries", label: "Travailleurs bénéficiaires", value: d.beneficiary_count, icon: "fa-users", open: () => this.openEmployees() },
            { key: "rate", label: "Taux de remboursement", value: this.percent(d.repayment_rate), icon: "fa-pie-chart", rate: d.repayment_rate },
        ];
    }

    money(value) {
        return formatMonetary(value, { currencyId: this.state.data.currency_id });
    }

    percent(value) {
        return formatPercentage(value, { digits: [false, 1] });
    }

    openLoans(extraDomain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Prêts accordés",
            res_model: "hr.employee.loan",
            views: [[false, "list"], [false, "form"]],
            domain: [...this.state.data.loan_domain, ...extraDomain],
        });
    }

    openUnit(unitId) {
        this.openLoans([["unit_id", "=", unitId]]);
    }

    openLines(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: state === "paid" ? "Échéances remboursées" : "Échéances à recouvrer",
            res_model: "hr.employee.loan.line",
            views: [[false, "list"]],
            domain: [...this.state.data.line_domain, ["state", "=", state]],
        });
    }

    openEmployees() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Travailleurs bénéficiaires",
            res_model: "hr.employee",
            views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", this.state.data.employee_ids]],
            context: {
                list_view_ref: "hr_employee_loan.hr_employee_view_list_simple",
                form_view_ref: "hr_employee_loan.hr_employee_view_form_simple",
                search_view_ref: "hr_employee_loan.hr_employee_view_search_simple",
            },
        });
    }
}

registry.category("actions").add("hr_employee_loan.dashboard", LoanDashboard);
