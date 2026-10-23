-- Schema applicativo Personale esportato il 2026-10-23. Solo database Supabase NUOVO e VUOTO.
BEGIN;
CREATE TABLE public."invoice_imports" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"document_key" text NOT NULL,
"direction" text NOT NULL,
"invoice_number" text NOT NULL,
"invoice_date" date NOT NULL,
"payment_date" date NOT NULL,
"subject" text NOT NULL,
"economic_year_id" uuid NOT NULL,
"document_year_id" uuid NOT NULL,
"vat_year_id" uuid,
"total" numeric(14,2) NOT NULL,
"record_ids" jsonb DEFAULT '{}'::jsonb NOT NULL,
"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE public."fiscal_years" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year" integer NOT NULL,
"status" text DEFAULT 'open'::text NOT NULL,
"notes" text,
"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE public."fiscal_parameters" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"code" text NOT NULL,
"description" text NOT NULL,
"value" numeric(18,6) NOT NULL,
"unit" text DEFAULT 'EUR'::text NOT NULL,
"source" text,
"source_date" date,
"is_provisional" boolean DEFAULT true NOT NULL,
"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE public."annual_settings" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"target_revenue_1" numeric(14,2),
"target_revenue_2" numeric(14,2),
"opening_reserve_balance" numeric(14,2) DEFAULT 0 NOT NULL,
"projection_mode" text DEFAULT 'observed_months'::text NOT NULL,
"notes" text
);
CREATE TABLE public."principals" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"name" text NOT NULL,
"enasarco_relationship" text DEFAULT 'plurimandatario'::text NOT NULL,
"start_date" date,
"end_date" date,
"active" boolean DEFAULT true NOT NULL,
"notes" text
);
CREATE TABLE public."monthly_revenues" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"principal_id" uuid NOT NULL,
"month" smallint NOT NULL,
"amount" numeric(14,2) NOT NULL,
"accrual_date" date,
"received_date" date,
"notes" text
);
CREATE TABLE public."vehicles" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"label" text NOT NULL,
"acquisition_cost_gross" numeric(14,2),
"acquisition_date" date,
"contract_start" date,
"contract_end" date,
"notes" text
);
CREATE TABLE public."vehicle_year_settings" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"vehicle_id" uuid NOT NULL,
"annual_km_limit" integer,
"excess_km_penalty" numeric(12,4),
"fiscal_cost_limit" numeric(14,2),
"notes" text
);
CREATE TABLE public."vehicle_monthly" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"vehicle_id" uuid NOT NULL,
"month" smallint NOT NULL,
"distance_km" numeric(12,2) NOT NULL,
"notes" text
);
CREATE TABLE public."cost_categories" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"code" text NOT NULL,
"name" text NOT NULL,
"vat_rate" numeric(9,6) DEFAULT 0 NOT NULL,
"vat_deductible_rate" numeric(9,6) DEFAULT 0 NOT NULL,
"cost_deductible_rate" numeric(9,6) DEFAULT 1 NOT NULL,
"deductible_limit" numeric(14,2),
"active" boolean DEFAULT true NOT NULL,
"notes" text
);
CREATE TABLE public."annual_cost_estimates" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"category_id" uuid NOT NULL,
"estimated_gross_amount" numeric(14,2) DEFAULT 0 NOT NULL,
"amount_includes_vat" boolean DEFAULT true NOT NULL,
"notes" text
);
CREATE TABLE public."estimate_monthly_allocations" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"estimate_id" uuid NOT NULL,
"month" smallint NOT NULL,
"planned_gross_amount" numeric(14,2) NOT NULL
);
CREATE TABLE public."costs" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"category_id" uuid NOT NULL,
"vehicle_id" uuid,
"expense_date" date NOT NULL,
"payment_date" date,
"description" text,
"gross_amount" numeric(14,2) NOT NULL,
"amount_includes_vat" boolean DEFAULT true NOT NULL,
"vat_rate" numeric(9,6) NOT NULL,
"vat_deductible_rate" numeric(9,6) NOT NULL,
"cost_deductible_rate" numeric(9,6) NOT NULL,
"deductible_limit" numeric(14,2),
"fiscal_competence_year" integer NOT NULL,
"notes" text,
"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE public."contributions" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"contribution_type" text NOT NULL,
"competence_year" integer NOT NULL,
"payment_date" date,
"amount" numeric(14,2) NOT NULL,
"deductible_amount" numeric(14,2) DEFAULT 0 NOT NULL,
"notes" text
);
CREATE TABLE public."tax_deductions" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"description" text NOT NULL,
"amount" numeric(14,2) NOT NULL,
"payment_date" date,
"deductible_limit" numeric(14,2),
"notes" text
);
CREATE TABLE public."tax_credits" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"description" text NOT NULL,
"original_amount" numeric(14,2) NOT NULL,
"credit_rate" numeric(9,6) NOT NULL,
"installment_count" smallint DEFAULT 1 NOT NULL,
"first_fiscal_year" integer NOT NULL,
"reference_expense_date" date,
"notes" text
);
CREATE TABLE public."monthly_reserves" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"month" smallint NOT NULL,
"reserved_amount" numeric(14,2) DEFAULT 0 NOT NULL,
"notes" text
);
CREATE TABLE public."vat_adjustments" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"month" smallint NOT NULL,
"adjustment_date" date,
"amount" numeric(14,2) NOT NULL,
"description" text NOT NULL,
"notes" text
);
CREATE TABLE public."monthly_net_commissions" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"month" integer NOT NULL,
"amount" numeric(14,2) NOT NULL
);
CREATE TABLE public."depreciable_assets" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"description" text NOT NULL,
"purchase_date" date NOT NULL,
"gross_amount" numeric(14,2) NOT NULL,
"deductible_vat" numeric(14,2) NOT NULL,
"depreciation_rate" numeric(9,6) NOT NULL,
"first_fiscal_year" integer NOT NULL,
"notes" text,
"version" integer DEFAULT 1 NOT NULL,
"is_planned" boolean DEFAULT false NOT NULL
);
CREATE TABLE public."purchase_vat_invoices" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"supplier" text NOT NULL,
"invoice_number" text NOT NULL,
"invoice_date" date NOT NULL,
"operation_date" date NOT NULL,
"received_date" date NOT NULL,
"registered_date" date NOT NULL,
"vat_amount" numeric(14,2) NOT NULL,
"deductible_vat" numeric(14,2) NOT NULL,
"category" text NOT NULL,
"anticipate" boolean DEFAULT false NOT NULL,
"notes" text
);
CREATE TABLE public."sales_vat_invoices" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"principal_id" uuid NOT NULL,
"invoice_number" text NOT NULL,
"invoice_date" date NOT NULL,
"vat_month" integer,
"document_type" text NOT NULL,
"taxable_amount" numeric(14,2) NOT NULL,
"vat_amount" numeric(14,2) NOT NULL,
"version" integer DEFAULT 1 NOT NULL,
"notes" text
);
CREATE TABLE public."vat_periods" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"frequency" text NOT NULL,
"month_from" integer NOT NULL,
"month_to" integer NOT NULL,
"opening_credit" numeric(14,2) NOT NULL,
"adjustment" numeric(14,2) NOT NULL,
"interest_amount" numeric(14,2) NOT NULL,
"paid_amount" numeric(14,2) NOT NULL,
"payment_date" date,
"documents_complete" boolean DEFAULT false NOT NULL,
"version" integer DEFAULT 1 NOT NULL
);
CREATE TABLE public."pension_payments" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"description" text NOT NULL,
"payment_date" date NOT NULL,
"amount" numeric(14,2) NOT NULL,
"version" integer DEFAULT 1 NOT NULL
);
CREATE TABLE public."purchase_cost_links" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"purchase_id" uuid NOT NULL,
"cost_id" uuid NOT NULL,
"version" integer DEFAULT 1 NOT NULL
);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_fiscal_year_check" CHECK (((fiscal_year >= 2000) AND (fiscal_year <= 2100)));
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_status_check" CHECK ((status = ANY (ARRAY['open'::text, 'closed'::text])));
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_pkey" PRIMARY KEY (id);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_user_id_fiscal_year_key" UNIQUE (user_id, fiscal_year);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_code_check" CHECK (((length(TRIM(BOTH FROM code)) >= 1) AND (length(TRIM(BOTH FROM code)) <= 100)));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_unit_check" CHECK ((unit = ANY (ARRAY['EUR'::text, 'RATE'::text, 'KM'::text, 'EUR_PER_KM'::text, 'COUNT'::text])));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_check" CHECK (((unit <> 'RATE'::text) OR ((value >= (0)::numeric) AND (value <= (2)::numeric))));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_pkey" PRIMARY KEY (id);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_user_id_fiscal_year_id_code_key" UNIQUE (user_id, fiscal_year_id, code);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_target_revenue_1_check" CHECK ((target_revenue_1 >= (0)::numeric));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_target_revenue_2_check" CHECK ((target_revenue_2 >= (0)::numeric));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_projection_mode_check" CHECK ((projection_mode = ANY (ARRAY['observed_months'::text, 'calendar_months'::text])));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_pkey" PRIMARY KEY (id);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_user_id_fiscal_year_id_key" UNIQUE (user_id, fiscal_year_id);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."principals" ADD CONSTRAINT "principals_name_check" CHECK ((length(TRIM(BOTH FROM name)) > 0));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_enasarco_relationship_check" CHECK ((enasarco_relationship = ANY (ARRAY['plurimandatario'::text, 'monomandatario'::text])));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_check" CHECK (((end_date IS NULL) OR (start_date IS NULL) OR (end_date >= start_date)));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_pkey" PRIMARY KEY (id);
ALTER TABLE public."principals" ADD CONSTRAINT "principals_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_user_id_fiscal_year_id_principal_id_month_key" UNIQUE (user_id, fiscal_year_id, principal_id, month);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_label_check" CHECK ((length(TRIM(BOTH FROM label)) > 0));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_acquisition_cost_gross_check" CHECK ((acquisition_cost_gross >= (0)::numeric));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_check" CHECK (((contract_end IS NULL) OR (contract_start IS NULL) OR (contract_end >= contract_start)));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_annual_km_limit_check" CHECK ((annual_km_limit >= 0));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_excess_km_penalty_check" CHECK ((excess_km_penalty >= (0)::numeric));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_fiscal_cost_limit_check" CHECK ((fiscal_cost_limit >= (0)::numeric));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_user_id_fiscal_year_id_vehicle_id_key" UNIQUE (user_id, fiscal_year_id, vehicle_id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_distance_km_check" CHECK ((distance_km >= (0)::numeric));
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_user_id_fiscal_year_id_vehicle_id_month_key" UNIQUE (user_id, fiscal_year_id, vehicle_id, month);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_code_check" CHECK (((length(TRIM(BOTH FROM code)) >= 1) AND (length(TRIM(BOTH FROM code)) <= 80)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_name_check" CHECK ((length(TRIM(BOTH FROM name)) > 0));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_vat_rate_check" CHECK (((vat_rate >= (0)::numeric) AND (vat_rate <= (1)::numeric)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_vat_deductible_rate_check" CHECK (((vat_deductible_rate >= (0)::numeric) AND (vat_deductible_rate <= (1)::numeric)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_cost_deductible_rate_check" CHECK (((cost_deductible_rate >= (0)::numeric) AND (cost_deductible_rate <= (1)::numeric)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_pkey" PRIMARY KEY (id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_user_id_fiscal_year_id_code_key" UNIQUE (user_id, fiscal_year_id, code);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_id_user_id_fiscal_year_id_key" UNIQUE (id, user_id, fiscal_year_id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_estimated_gross_amount_check" CHECK ((estimated_gross_amount >= (0)::numeric));
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_pkey" PRIMARY KEY (id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_user_id_fiscal_year_id_category_id_key" UNIQUE (user_id, fiscal_year_id, category_id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_id_user_id_fiscal_year_id_key" UNIQUE (id, user_id, fiscal_year_id);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_planned_gross_amount_check" CHECK ((planned_gross_amount >= (0)::numeric));
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_pkey" PRIMARY KEY (id);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_user_id_estimate_id_month_key" UNIQUE (user_id, estimate_id, month);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."costs" ADD CONSTRAINT "costs_gross_amount_check" CHECK ((gross_amount >= (0)::numeric));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vat_rate_check" CHECK (((vat_rate >= (0)::numeric) AND (vat_rate <= (1)::numeric)));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vat_deductible_rate_check" CHECK (((vat_deductible_rate >= (0)::numeric) AND (vat_deductible_rate <= (1)::numeric)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_cost_deductible_rate_check" CHECK (((cost_deductible_rate >= (0)::numeric) AND (cost_deductible_rate <= (1)::numeric)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_fiscal_competence_year_check" CHECK (((fiscal_competence_year >= 2000) AND (fiscal_competence_year <= 2100)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_pkey" PRIMARY KEY (id);
ALTER TABLE public."costs" ADD CONSTRAINT "costs_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_contribution_type_check" CHECK ((contribution_type = ANY (ARRAY['inps_fixed'::text, 'inps_excess'::text, 'enasarco'::text, 'other'::text])));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_competence_year_check" CHECK (((competence_year >= 2000) AND (competence_year <= 2100)));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_deductible_amount_check" CHECK ((deductible_amount >= (0)::numeric));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_check" CHECK ((deductible_amount <= amount));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_pkey" PRIMARY KEY (id);
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_pkey" PRIMARY KEY (id);
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_original_amount_check" CHECK ((original_amount >= (0)::numeric));
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_pkey" PRIMARY KEY (id);
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_credit_rate_check" CHECK (((credit_rate >= (0)::numeric) AND (credit_rate <= (2)::numeric)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_installment_count_check" CHECK (((installment_count >= 1) AND (installment_count <= 30)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_first_fiscal_year_check" CHECK (((first_fiscal_year >= 2000) AND (first_fiscal_year <= 2100)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_pkey" PRIMARY KEY (id);
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_reserved_amount_check" CHECK ((reserved_amount >= (0)::numeric));
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_user_id_fiscal_year_id_month_key" UNIQUE (user_id, fiscal_year_id, month);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_fiscal_year_id_month_key" UNIQUE (fiscal_year_id, month);
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_supplier_check" CHECK (((length(btrim(supplier)) >= 1) AND (length(btrim(supplier)) <= 200)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_invoice_number_check" CHECK (((length(btrim(invoice_number)) >= 1) AND (length(btrim(invoice_number)) <= 100)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_vat_amount_check" CHECK ((vat_amount >= (0)::numeric));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check" CHECK (((deductible_vat >= (0)::numeric) AND (deductible_vat <= vat_amount)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_category_check" CHECK ((category = ANY (ARRAY['auto'::text, 'altro'::text])));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_notes_check" CHECK (((notes IS NULL) OR (length(notes) <= 500)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check1" CHECK ((received_date >= operation_date));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check2" CHECK ((registered_date >= received_date));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_pkey" PRIMARY KEY (id);
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_description_check" CHECK (((length(btrim(description)) >= 1) AND (length(btrim(description)) <= 200)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_gross_amount_check" CHECK ((gross_amount >= (0)::numeric));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_check" CHECK (((deductible_vat >= (0)::numeric) AND (deductible_vat <= gross_amount)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_depreciation_rate_check" CHECK (((depreciation_rate > (0)::numeric) AND (depreciation_rate <= (1)::numeric)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_first_fiscal_year_check" CHECK (((first_fiscal_year >= 2000) AND (first_fiscal_year <= 2100)));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_check2" CHECK ((((paid_amount = (0)::numeric) AND (payment_date IS NULL)) OR ((paid_amount > (0)::numeric) AND (payment_date IS NOT NULL) AND (payment_date <= CURRENT_DATE))));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_pkey" PRIMARY KEY (id);
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_notes_check" CHECK (((notes IS NULL) OR (length(notes) <= 500)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_pkey" PRIMARY KEY (id);
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_purchase_date_status_check" CHECK ((is_planned OR (purchase_date <= CURRENT_DATE)));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_invoice_number_check" CHECK (((length(btrim(invoice_number)) >= 1) AND (length(btrim(invoice_number)) <= 100)));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_invoice_date_check" CHECK ((invoice_date <= CURRENT_DATE));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_vat_month_check" CHECK (((vat_month >= 1) AND (vat_month <= 12)));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_document_type_check" CHECK ((document_type = ANY (ARRAY['fattura'::text, 'nota_credito'::text])));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_taxable_amount_check" CHECK ((taxable_amount >= (0)::numeric));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_vat_amount_check" CHECK ((vat_amount >= (0)::numeric));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_notes_check" CHECK (((notes IS NULL) OR (length(notes) <= 500)));
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_pkey" PRIMARY KEY (id);
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_frequency_check" CHECK ((frequency = ANY (ARRAY['mensile'::text, 'trimestrale'::text])));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_month_from_check" CHECK (((month_from >= 1) AND (month_from <= 12)));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_check" CHECK (((month_to >= month_from) AND (month_to <= 12)));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_opening_credit_check" CHECK ((opening_credit >= (0)::numeric));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_interest_amount_check" CHECK ((interest_amount >= (0)::numeric));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_paid_amount_check" CHECK ((paid_amount >= (0)::numeric));
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_check1" CHECK ((((frequency = 'mensile'::text) AND (month_from = month_to)) OR ((frequency = 'trimestrale'::text) AND (month_from = ANY (ARRAY[1, 4, 7, 10])) AND (month_to = (month_from + 2)))));
ALTER TABLE public."pension_payments" ADD CONSTRAINT "pension_payments_description_check" CHECK (((length(btrim(description)) >= 1) AND (length(btrim(description)) <= 200)));
ALTER TABLE public."pension_payments" ADD CONSTRAINT "pension_payments_payment_date_check" CHECK ((payment_date <= CURRENT_DATE));
ALTER TABLE public."pension_payments" ADD CONSTRAINT "pension_payments_amount_check" CHECK ((amount > (0)::numeric));
ALTER TABLE public."pension_payments" ADD CONSTRAINT "pension_payments_pkey" PRIMARY KEY (id);
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_pkey" PRIMARY KEY (id);
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_purchase_id_key" UNIQUE (purchase_id);
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_cost_id_key" UNIQUE (cost_id);
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_document_key_check" CHECK (((length(document_key) >= 1) AND (length(document_key) <= 500)));
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_direction_check" CHECK ((direction = ANY (ARRAY['emessa'::text, 'ricevuta'::text])));
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_total_check" CHECK ((total > (0)::numeric));
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_pkey" PRIMARY KEY (id);
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_user_id_document_key_key" UNIQUE (user_id, document_key);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."principals" ADD CONSTRAINT "principals_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_principal_id_user_id_fkey" FOREIGN KEY (principal_id, user_id) REFERENCES principals(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_category_id_user_id_fiscal_year_id_fkey" FOREIGN KEY (category_id, user_id, fiscal_year_id) REFERENCES cost_categories(id, user_id, fiscal_year_id) ON DELETE RESTRICT;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_estimate_id_user_id_fiscal_ye_fkey" FOREIGN KEY (estimate_id, user_id, fiscal_year_id) REFERENCES annual_cost_estimates(id, user_id, fiscal_year_id) ON DELETE CASCADE;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_category_id_user_id_fiscal_year_id_fkey" FOREIGN KEY (category_id, user_id, fiscal_year_id) REFERENCES cost_categories(id, user_id, fiscal_year_id) ON DELETE RESTRICT;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."vat_periods" ADD CONSTRAINT "vat_periods_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."sales_vat_invoices" ADD CONSTRAINT "sales_vat_invoices_principal_id_fkey" FOREIGN KEY (principal_id) REFERENCES principals(id) ON DELETE RESTRICT;
ALTER TABLE public."pension_payments" ADD CONSTRAINT "pension_payments_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_purchase_id_fkey" FOREIGN KEY (purchase_id) REFERENCES purchase_vat_invoices(id) ON DELETE RESTRICT;
ALTER TABLE public."purchase_cost_links" ADD CONSTRAINT "purchase_cost_links_cost_id_fkey" FOREIGN KEY (cost_id) REFERENCES costs(id) ON DELETE RESTRICT;
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id);
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_economic_year_id_fkey" FOREIGN KEY (economic_year_id) REFERENCES fiscal_years(id);
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_document_year_id_fkey" FOREIGN KEY (document_year_id) REFERENCES fiscal_years(id);
ALTER TABLE public."invoice_imports" ADD CONSTRAINT "invoice_imports_vat_year_id_fkey" FOREIGN KEY (vat_year_id) REFERENCES fiscal_years(id);
CREATE OR REPLACE FUNCTION public.piva_validate_depreciable_asset()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare fy public.fiscal_years%rowtype;
begin
  select * into fy from public.fiscal_years where id=new.fiscal_year_id;
  if fy.id is null or fy.user_id is distinct from auth.uid() or fy.status <> 'open' then
    raise exception 'Anno di acquisto non accessibile o chiuso';
  end if;
  if extract(year from new.purchase_date) <> fy.fiscal_year
     or new.first_fiscal_year <> fy.fiscal_year then
    raise exception 'Data/anno del bene non coerenti con anno di acquisto';
  end if;
  if not new.is_planned and new.purchase_date > current_date then
    raise exception 'Un bene acquistato non può avere una data futura';
  end if;
  if tg_op='UPDATE' then
    if new.fiscal_year_id is distinct from old.fiscal_year_id then
      raise exception 'Spostamento tra anni non consentito';
    end if;
    new.version:=old.version+1;
  end if;
  return new;
end $function$
;
CREATE OR REPLACE FUNCTION public.piva_validate_fiscal_year_status()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
begin
  if new.id is distinct from old.id
     or new.user_id is distinct from old.user_id
     or new.fiscal_year is distinct from old.fiscal_year then
    raise exception 'Per un anno fiscale è modificabile soltanto lo stato';
  end if;

  if old.status not in ('open','closed')
     or new.status not in ('open','closed') then
    raise exception 'Stato anno fiscale non valido';
  end if;

  if new.status = old.status then
    return new;
  end if;

  if not (
       (old.status='open' and new.status='closed')
       or (old.status='closed' and new.status='open')
     ) then
    raise exception 'Transizione stato anno fiscale non consentita';
  end if;

  return new;
end $function$
;
CREATE OR REPLACE FUNCTION public.piva_validate_structure_record()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare fy public.fiscal_years%rowtype;
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.fiscal_year_id::text, 91827));
  select * into fy from public.fiscal_years where id = new.fiscal_year_id;
  if fy.id is null or fy.user_id is distinct from auth.uid() or fy.status <> 'open' then
    raise exception 'Anno non accessibile o chiuso';
  end if;
  if tg_op = 'UPDATE' then
    if new.fiscal_year_id is distinct from old.fiscal_year_id then
      raise exception 'Spostamento tra anni non consentito';
    end if;
    new.version := old.version + 1;
  else
    new.version := 1;
  end if;
  if tg_table_name = 'sales_vat_invoices' then
    if extract(year from new.invoice_date) <> fy.fiscal_year or new.invoice_date > current_date or new.vat_month is null then
      raise exception 'Data documento fuori anno/futura o mese IVA da confermare';
    end if;
  elsif tg_table_name = 'pension_payments' then
    if extract(year from new.payment_date) <> fy.fiscal_year then
      raise exception 'Pagamento pensione fuori anno';
    end if;
  elsif tg_table_name = 'vat_periods' then
    -- Lock transazionale per anno: non richiede UPDATE sulla tabella fiscal_years.
    if exists (select 1 from public.vat_periods p where p.fiscal_year_id = new.fiscal_year_id
               and p.id <> new.id and p.month_from <= new.month_to and p.month_to >= new.month_from) then
      raise exception 'Periodi sovrapposti' using errcode = '23P01';
    end if;
  elsif tg_table_name = 'purchase_cost_links' then
    if not exists (select 1 from public.purchase_vat_invoices p
                   where p.id = new.purchase_id and p.fiscal_year_id = new.fiscal_year_id)
       or not exists (select 1 from public.costs c
                      where c.id = new.cost_id and c.fiscal_year_id = new.fiscal_year_id) then
      raise exception 'Costo o fattura non visibile o appartenente a un altro anno';
    end if;
  end if;
  return new;
end $function$
;
CREATE OR REPLACE FUNCTION public.piva_import_invoice(p jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
declare
 uid uuid:=auth.uid(); imp uuid:=gen_random_uuid(); economic public.fiscal_years%rowtype; document public.fiscal_years%rowtype; vy public.fiscal_years%rowtype;
 cat public.cost_categories%rowtype; rev public.monthly_revenues%rowtype;
 d date:=(p->>'invoice_date')::date; pay date:=(p->>'payment_date')::date;
 received date; registered date; year_id uuid; rec uuid; purchase uuid; sale uuid; asset_id uuid; asset_year public.fiscal_years%rowtype; asset_date date; asset_rate numeric; asset_description text; is_asset boolean:=coalesce(p->>'purchase_kind','expense')='asset'; costs jsonb:='[]';
 b numeric:=0; v numeric:=0; total numeric:=(p->>'total')::numeric; deductible numeric;
 g jsonb; gb numeric; gv numeric; gr numeric; key text; subject text:=btrim(p->>'subject'); number text:=btrim(p->>'invoice_number');
begin
 if uid is null then raise exception 'Sessione scaduta'; end if;
 if p->>'direction' not in ('emessa','ricevuta') or subject is null or length(subject) not between 1 and 200 or number is null or length(number) not between 1 and 100 or d is null or pay is null or d>current_date or pay>current_date then raise exception 'Dati fattura non validi'; end if;
 if jsonb_typeof(p->'groups') is distinct from 'array' or jsonb_array_length(p->'groups') not between 1 and 30 then raise exception 'Riepilogo IVA mancante'; end if;
 for g in select value from jsonb_array_elements(p->'groups') loop
  gb:=(g->>'base')::numeric; gv:=(g->>'vat')::numeric; gr:=(g->>'rate')::numeric;
  if gb is null or gv is null or gr is null or gb<0 or gv<0 or gb<>round(gb,2) or gv<>round(gv,2) or gr not in (0,4,5,10,22) or coalesce(g->>'payability','I') not in ('','I') then raise exception 'Importi o esigibilita IVA non supportati'; end if;
  if (gr=0 and (coalesce(g->>'nature','')!~'^N[1-7](\.[0-9])?$' or gv<>0)) or (gr>0 and (coalesce(g->>'nature','')<>'' or abs(round(gb*gr/100,2)-gv)>0.01)) then raise exception 'IVA incoerente'; end if;
  b:=b+gb;v:=v+gv;
 end loop;
 if total is null or total<=0 or total<>round(total,2) or total<>b+v or (p->>'base')::numeric is distinct from b or (p->>'vat')::numeric is distinct from v then raise exception 'Totali incoerenti'; end if;
 -- Use the same advisory key as year closure; deterministic ordering prevents deadlocks.
 for year_id in select distinct x from unnest(array[(p->>'economic_year_id')::uuid,(p->>'document_year_id')::uuid,nullif(p->>'vat_year_id','')::uuid,nullif(p->>'asset_year_id','')::uuid]) x where x is not null order by x loop
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(year_id::text,91827));
  if not exists(select 1 from public.fiscal_years f where f.id=year_id and f.user_id=uid and f.status='open') then raise exception 'Anno mancante, chiuso o non accessibile'; end if;
 end loop;
 select * into economic from public.fiscal_years where id=(p->>'economic_year_id')::uuid and user_id=uid for share;
 select * into document from public.fiscal_years where id=(p->>'document_year_id')::uuid and user_id=uid for share;
 if economic.id is null or document.id is null or economic.fiscal_year<>extract(year from pay) or document.fiscal_year<>extract(year from d) then raise exception 'Anno di destinazione errato'; end if;
 key:=concat(p->>'direction','|',coalesce(nullif(btrim(p->>'tax_id'),''),lower(subject)),'|',lower(number),'|',d::text);
 if exists(select 1 from public.invoice_imports where user_id=uid and document_key=key) then raise exception 'Fattura gia importata'; end if;
 if p->>'direction'='emessa' then
  if is_asset then raise exception 'Un bene puo essere importato solo da fattura ricevuta'; end if;
  if (document.fiscal_year=2026 and v<>0) or (document.fiscal_year<>2026 and exists(select 1 from jsonb_array_elements(p->'groups') x where (x->>'rate')::numeric<>22)) or (document.fiscal_year=2026)<>(economic.fiscal_year=2026) then raise exception 'Regime o IVA vendita non compatibili'; end if;
  if not exists(select 1 from public.principals pr where pr.id=(p->>'principal_id')::uuid and pr.user_id=uid) then raise exception 'Mandante non accessibile'; end if;
  select * into rev from public.monthly_revenues r where r.fiscal_year_id=economic.id and r.principal_id=(p->>'principal_id')::uuid and r.month=extract(month from pay) for update;
  if rev.amount is distinct from nullif(p->>'previous_amount','')::numeric then raise exception 'Fatturato cambiato: aggiorna e controlla nuovamente l’anteprima'; end if;
  if rev.id is null then
   insert into public.monthly_revenues(fiscal_year_id,principal_id,month,amount,accrual_date,received_date,notes) values(economic.id,(p->>'principal_id')::uuid,extract(month from pay),b,d,pay,'Importazione fattura '||number) returning id into rec;
  else
   -- Drop the gross-entry marker after incrementing the net aggregate; retain other notes.
   update public.monthly_revenues set amount=amount+b,notes=split_part(coalesce(notes,''),chr(10)||'[PIVA_GROSS_22_V1]',1) where id=rev.id returning id into rec;
  end if;
  if document.fiscal_year<>2026 then
   insert into public.sales_vat_invoices(fiscal_year_id,principal_id,invoice_number,invoice_date,vat_month,document_type,taxable_amount,vat_amount,notes) values(document.id,(p->>'principal_id')::uuid,number,d,extract(month from d),'fattura',b,v,'Importazione '||imp) returning id into sale;
  end if;
 else
  if not is_asset then
  select * into cat from public.cost_categories where id=(p->>'category_id')::uuid and fiscal_year_id=economic.id and user_id=uid;
  if cat.id is null or cat.code in ('pc','telefono_tablet','penale_km') then raise exception 'Categoria non accessibile o richiede modulo completo'; end if;
  if cat.code in ('rate_auto','carburante','autostrada','manutenzione_auto','assicurazione','bollo') and not exists(select 1 from public.vehicles ve where ve.id=(p->>'vehicle_id')::uuid and ve.user_id=uid) then raise exception 'Auto non accessibile'; end if;
  end if;
  received:=(p->>'received_date')::date;registered:=(p->>'registered_date')::date;deductible:=(p->>'deductible_vat')::numeric;
  select * into vy from public.fiscal_years where id=(p->>'vat_year_id')::uuid and user_id=uid for share;
  if received is null or registered is null or received<d or registered<received or registered>current_date or vy.id is null or vy.fiscal_year<>extract(year from registered) or deductible is null or deductible<0 or deductible>v or deductible<>round(deductible,2) or (vy.fiscal_year=2026 and deductible<>0) then raise exception 'Date o IVA detraibile non valide'; end if;
  if not is_asset and (p->>'vat_category') is distinct from (case when cat.code in ('rate_auto','carburante','autostrada','manutenzione_auto','assicurazione','bollo') then 'auto' else 'altro' end) then raise exception 'Categoria IVA errata'; end if;
  if exists(select 1 from public.purchase_vat_invoices pi where lower(btrim(pi.supplier))=lower(subject) and lower(btrim(pi.invoice_number))=lower(number) and pi.invoice_date=d) then raise exception 'Fattura gia presente nel registro IVA'; end if;
  if is_asset then
   asset_date:=(p->>'asset_purchase_date')::date; asset_rate:=(p->>'asset_rate')::numeric;asset_description:=btrim(p->>'asset_description');
   select * into asset_year from public.fiscal_years where id=(p->>'asset_year_id')::uuid and user_id=uid for share;
   if asset_date is null or asset_date>current_date or asset_year.id is null or asset_year.status<>'open' or asset_year.fiscal_year<>extract(year from asset_date) or asset_description is null or length(asset_description) not between 1 and 200 or (p->>'vat_category') not in ('auto','altro') then raise exception 'Dati bene non validi';end if;
   if (asset_year.fiscal_year=2026)<>(vy.fiscal_year=2026) then raise exception 'Cambio regime: verifica manuale richiesta';end if;
   if total-deductible<=516.46 then asset_rate:=1;end if;
   if asset_rate is null or asset_rate<=0 or asset_rate>1 or asset_rate<>round(asset_rate,6) then raise exception 'Coefficiente ammortamento non valido';end if;
   if exists(select 1 from public.depreciable_assets a where not a.is_planned and a.purchase_date=asset_date and lower(btrim(a.description))=lower(asset_description) and a.gross_amount=total) then raise exception 'Bene gia registrato';end if;
   insert into public.depreciable_assets(fiscal_year_id,description,purchase_date,gross_amount,deductible_vat,depreciation_rate,first_fiscal_year,is_planned,notes)
   values(asset_year.id,asset_description,asset_date,total,deductible,asset_rate,asset_year.fiscal_year,false,'Importazione fattura '||number||' · '||imp) returning id into asset_id;
  else
  for g in select value from jsonb_array_elements(p->'groups') loop
   gb:=(g->>'base')::numeric;gv:=(g->>'vat')::numeric;gr:=(g->>'rate')::numeric;
   if gb+gv>0 then
    insert into public.costs(fiscal_year_id,category_id,vehicle_id,expense_date,payment_date,description,gross_amount,amount_includes_vat,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,fiscal_competence_year,notes)
    values(economic.id,cat.id,nullif(p->>'vehicle_id','')::uuid,pay,pay,left(subject||' · fattura '||number,200),gb+gv,true,case when economic.fiscal_year=2026 then 0 else gr/100 end,case when v=0 or economic.fiscal_year=2026 then 0 else deductible/v end,cat.cost_deductible_rate,cat.deductible_limit,economic.fiscal_year,'Importazione '||imp||' · IVA documento '||gv) returning id into rec;
    costs:=costs||jsonb_build_array(rec);
   end if;
  end loop;
  end if;
  if vy.fiscal_year<>2026 then
   insert into public.purchase_vat_invoices(fiscal_year_id,supplier,invoice_number,invoice_date,operation_date,received_date,registered_date,vat_amount,deductible_vat,category,anticipate,notes)
   values(vy.id,subject,number,d,d,received,registered,v,deductible,p->>'vat_category',false,'Importazione '||imp) returning id into purchase;
  end if;
 end if;
 insert into public.invoice_imports(id,user_id,document_key,direction,invoice_number,invoice_date,payment_date,subject,economic_year_id,document_year_id,vat_year_id,total,record_ids)
 values(imp,uid,key,p->>'direction',number,d,pay,subject,economic.id,document.id,nullif(p->>'vat_year_id','')::uuid,total,jsonb_build_object('costs',costs,'asset',asset_id,'revenue',case when p->>'direction'='emessa' then rec else null end,'purchase',purchase,'sale',sale));
 return imp;
end $function$
;
CREATE INDEX invoice_import_year_idx ON public.invoice_imports USING btree (economic_year_id);
CREATE INDEX invoice_import_document_year_idx ON public.invoice_imports USING btree (document_year_id);
CREATE INDEX invoice_import_vat_year_idx ON public.invoice_imports USING btree (vat_year_id);
CREATE INDEX fiscal_parameters_user_id_fiscal_year_id_idx ON public.fiscal_parameters USING btree (user_id, fiscal_year_id);
CREATE INDEX monthly_revenues_user_id_fiscal_year_id_month_idx ON public.monthly_revenues USING btree (user_id, fiscal_year_id, month);
CREATE INDEX vehicle_monthly_user_id_fiscal_year_id_month_idx ON public.vehicle_monthly USING btree (user_id, fiscal_year_id, month);
CREATE INDEX costs_user_id_fiscal_year_id_expense_date_idx ON public.costs USING btree (user_id, fiscal_year_id, expense_date);
CREATE INDEX contributions_user_id_payment_date_idx ON public.contributions USING btree (user_id, payment_date);
CREATE INDEX tax_deductions_user_id_fiscal_year_id_idx ON public.tax_deductions USING btree (user_id, fiscal_year_id);
CREATE INDEX tax_credits_user_id_first_fiscal_year_idx ON public.tax_credits USING btree (user_id, first_fiscal_year);
CREATE INDEX vat_adjustments_user_id_fiscal_year_id_month_idx ON public.vat_adjustments USING btree (user_id, fiscal_year_id, month);
CREATE INDEX depreciable_assets_year_idx ON public.depreciable_assets USING btree (fiscal_year_id);
CREATE UNIQUE INDEX purchase_vat_invoice_identity ON public.purchase_vat_invoices USING btree (fiscal_year_id, lower(btrim(supplier)), lower(btrim(invoice_number)), invoice_date);
CREATE INDEX purchase_vat_invoices_fiscal_year_idx ON public.purchase_vat_invoices USING btree (fiscal_year_id);
CREATE UNIQUE INDEX sales_vat_identity ON public.sales_vat_invoices USING btree (fiscal_year_id, principal_id, lower(btrim(invoice_number)), invoice_date, document_type);
CREATE INDEX sales_vat_invoices_year_idx ON public.sales_vat_invoices USING btree (fiscal_year_id);
CREATE INDEX vat_periods_year_idx ON public.vat_periods USING btree (fiscal_year_id);
CREATE UNIQUE INDEX pension_payment_identity ON public.pension_payments USING btree (fiscal_year_id, payment_date, lower(btrim(description)), amount);
CREATE INDEX pension_payments_year_idx ON public.pension_payments USING btree (fiscal_year_id);
CREATE INDEX purchase_cost_links_year_idx ON public.purchase_cost_links USING btree (fiscal_year_id);
CREATE TRIGGER piva_validate_depreciable_asset BEFORE INSERT OR UPDATE ON public.depreciable_assets FOR EACH ROW EXECUTE FUNCTION piva_validate_depreciable_asset();
CREATE TRIGGER piva_validate_fiscal_year_status BEFORE UPDATE ON public.fiscal_years FOR EACH ROW EXECUTE FUNCTION piva_validate_fiscal_year_status();
CREATE TRIGGER piva_validate_record BEFORE INSERT OR UPDATE ON public.sales_vat_invoices FOR EACH ROW EXECUTE FUNCTION piva_validate_structure_record();
CREATE TRIGGER piva_validate_record BEFORE INSERT OR UPDATE ON public.vat_periods FOR EACH ROW EXECUTE FUNCTION piva_validate_structure_record();
CREATE TRIGGER piva_validate_record BEFORE INSERT OR UPDATE ON public.pension_payments FOR EACH ROW EXECUTE FUNCTION piva_validate_structure_record();
CREATE TRIGGER piva_validate_record BEFORE INSERT OR UPDATE ON public.purchase_cost_links FOR EACH ROW EXECUTE FUNCTION piva_validate_structure_record();
ALTER TABLE public."invoice_imports" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."invoice_imports" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."fiscal_years" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."fiscal_years" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."fiscal_parameters" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."fiscal_parameters" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."annual_settings" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."annual_settings" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."principals" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."principals" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."monthly_revenues" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."monthly_revenues" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."vehicles" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."vehicles" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."vehicle_year_settings" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."vehicle_year_settings" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."vehicle_monthly" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."vehicle_monthly" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."cost_categories" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."cost_categories" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."annual_cost_estimates" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."annual_cost_estimates" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."estimate_monthly_allocations" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."estimate_monthly_allocations" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."costs" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."costs" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."contributions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."contributions" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."tax_deductions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."tax_deductions" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."tax_credits" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."tax_credits" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."monthly_reserves" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."monthly_reserves" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."vat_adjustments" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."vat_adjustments" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."monthly_net_commissions" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."monthly_net_commissions" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."depreciable_assets" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."depreciable_assets" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."purchase_vat_invoices" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."purchase_vat_invoices" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."sales_vat_invoices" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."sales_vat_invoices" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."vat_periods" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."vat_periods" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."pension_payments" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."pension_payments" FROM PUBLIC,anon,authenticated;
ALTER TABLE public."purchase_cost_links" ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public."purchase_cost_links" FROM PUBLIC,anon,authenticated;
CREATE POLICY "invoice_import_insert" ON public."invoice_imports" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK (((user_id = ( SELECT auth.uid() AS uid)) AND (EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = invoice_imports.economic_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))) AND (EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = invoice_imports.document_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))) AND ((vat_year_id IS NULL) OR (EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = invoice_imports.vat_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))))));
CREATE POLICY "invoice_import_read" ON public."invoice_imports" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."fiscal_years" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."fiscal_years" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."fiscal_years" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."fiscal_years" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_fiscal_year_update_owner" ON public."fiscal_years" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_fiscal_year_update_owner_guard" ON public."fiscal_years" AS RESTRICTIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."fiscal_parameters" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."fiscal_parameters" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."fiscal_parameters" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."fiscal_parameters" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."annual_settings" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."annual_settings" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."annual_settings" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."annual_settings" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."principals" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."principals" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."principals" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."principals" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."monthly_revenues" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."monthly_revenues" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."monthly_revenues" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."monthly_revenues" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicles" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicles" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicles" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."vehicles" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicle_year_settings" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicle_year_settings" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicle_year_settings" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."vehicle_year_settings" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicle_monthly" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicle_monthly" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicle_monthly" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."vehicle_monthly" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."cost_categories" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."cost_categories" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."cost_categories" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."cost_categories" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."annual_cost_estimates" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."annual_cost_estimates" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."annual_cost_estimates" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."annual_cost_estimates" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."costs" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."costs" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."costs" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."costs" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."contributions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."contributions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."contributions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."contributions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."tax_deductions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."tax_deductions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."tax_deductions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."tax_deductions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."tax_credits" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."tax_credits" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."tax_credits" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."tax_credits" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."monthly_reserves" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."monthly_reserves" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."monthly_reserves" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."monthly_reserves" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vat_adjustments" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vat_adjustments" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vat_adjustments" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."vat_adjustments" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "net_commissions_delete_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "net_commissions_insert_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "net_commissions_select_owner" ON public."monthly_net_commissions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "net_commissions_update_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "piva_depreciable_delete" ON public."depreciable_assets" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_depreciable_insert" ON public."depreciable_assets" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_depreciable_read" ON public."depreciable_assets" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_depreciable_update" ON public."depreciable_assets" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "purchase_vat_delete_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "purchase_vat_insert_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "purchase_vat_select_owner" ON public."purchase_vat_invoices" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "purchase_vat_update_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "piva_delete" ON public."sales_vat_invoices" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = sales_vat_invoices.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_insert" ON public."sales_vat_invoices" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = sales_vat_invoices.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_principal_guard" ON public."sales_vat_invoices" AS RESTRICTIVE FOR ALL TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM principals p
  WHERE ((p.id = sales_vat_invoices.principal_id) AND (p.user_id = ( SELECT auth.uid() AS uid)))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM principals p
  WHERE ((p.id = sales_vat_invoices.principal_id) AND (p.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_read" ON public."sales_vat_invoices" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = sales_vat_invoices.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_update" ON public."sales_vat_invoices" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = sales_vat_invoices.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = sales_vat_invoices.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_delete" ON public."vat_periods" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = vat_periods.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_insert" ON public."vat_periods" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = vat_periods.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_read" ON public."vat_periods" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = vat_periods.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_update" ON public."vat_periods" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = vat_periods.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = vat_periods.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_delete" ON public."pension_payments" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = pension_payments.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_insert" ON public."pension_payments" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = pension_payments.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_read" ON public."pension_payments" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = pension_payments.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_update" ON public."pension_payments" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = pension_payments.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = pension_payments.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_delete" ON public."purchase_cost_links" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = purchase_cost_links.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_insert" ON public."purchase_cost_links" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = purchase_cost_links.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "piva_read" ON public."purchase_cost_links" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = purchase_cost_links.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "piva_update" ON public."purchase_cost_links" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = purchase_cost_links.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = purchase_cost_links.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
GRANT INSERT ON public."invoice_imports" TO "authenticated";
GRANT SELECT ON public."invoice_imports" TO "authenticated";
GRANT INSERT ON public."fiscal_years" TO "authenticated";
GRANT SELECT ON public."fiscal_years" TO "authenticated";
GRANT UPDATE ON public."fiscal_years" TO "authenticated";
GRANT DELETE ON public."fiscal_years" TO "authenticated";
GRANT TRUNCATE ON public."fiscal_years" TO "authenticated";
GRANT REFERENCES ON public."fiscal_years" TO "authenticated";
GRANT TRIGGER ON public."fiscal_years" TO "authenticated";
GRANT INSERT ON public."fiscal_parameters" TO "authenticated";
GRANT SELECT ON public."fiscal_parameters" TO "authenticated";
GRANT UPDATE ON public."fiscal_parameters" TO "authenticated";
GRANT DELETE ON public."fiscal_parameters" TO "authenticated";
GRANT TRUNCATE ON public."fiscal_parameters" TO "authenticated";
GRANT REFERENCES ON public."fiscal_parameters" TO "authenticated";
GRANT TRIGGER ON public."fiscal_parameters" TO "authenticated";
GRANT INSERT ON public."annual_settings" TO "authenticated";
GRANT SELECT ON public."annual_settings" TO "authenticated";
GRANT UPDATE ON public."annual_settings" TO "authenticated";
GRANT DELETE ON public."annual_settings" TO "authenticated";
GRANT TRUNCATE ON public."annual_settings" TO "authenticated";
GRANT REFERENCES ON public."annual_settings" TO "authenticated";
GRANT TRIGGER ON public."annual_settings" TO "authenticated";
GRANT INSERT ON public."principals" TO "authenticated";
GRANT SELECT ON public."principals" TO "authenticated";
GRANT UPDATE ON public."principals" TO "authenticated";
GRANT DELETE ON public."principals" TO "authenticated";
GRANT TRUNCATE ON public."principals" TO "authenticated";
GRANT REFERENCES ON public."principals" TO "authenticated";
GRANT TRIGGER ON public."principals" TO "authenticated";
GRANT INSERT ON public."monthly_revenues" TO "authenticated";
GRANT SELECT ON public."monthly_revenues" TO "authenticated";
GRANT UPDATE ON public."monthly_revenues" TO "authenticated";
GRANT DELETE ON public."monthly_revenues" TO "authenticated";
GRANT TRUNCATE ON public."monthly_revenues" TO "authenticated";
GRANT REFERENCES ON public."monthly_revenues" TO "authenticated";
GRANT TRIGGER ON public."monthly_revenues" TO "authenticated";
GRANT INSERT ON public."vehicles" TO "authenticated";
GRANT SELECT ON public."vehicles" TO "authenticated";
GRANT UPDATE ON public."vehicles" TO "authenticated";
GRANT DELETE ON public."vehicles" TO "authenticated";
GRANT TRUNCATE ON public."vehicles" TO "authenticated";
GRANT REFERENCES ON public."vehicles" TO "authenticated";
GRANT TRIGGER ON public."vehicles" TO "authenticated";
GRANT INSERT ON public."vehicle_year_settings" TO "authenticated";
GRANT SELECT ON public."vehicle_year_settings" TO "authenticated";
GRANT UPDATE ON public."vehicle_year_settings" TO "authenticated";
GRANT DELETE ON public."vehicle_year_settings" TO "authenticated";
GRANT TRUNCATE ON public."vehicle_year_settings" TO "authenticated";
GRANT REFERENCES ON public."vehicle_year_settings" TO "authenticated";
GRANT TRIGGER ON public."vehicle_year_settings" TO "authenticated";
GRANT INSERT ON public."vehicle_monthly" TO "authenticated";
GRANT SELECT ON public."vehicle_monthly" TO "authenticated";
GRANT UPDATE ON public."vehicle_monthly" TO "authenticated";
GRANT DELETE ON public."vehicle_monthly" TO "authenticated";
GRANT TRUNCATE ON public."vehicle_monthly" TO "authenticated";
GRANT REFERENCES ON public."vehicle_monthly" TO "authenticated";
GRANT TRIGGER ON public."vehicle_monthly" TO "authenticated";
GRANT INSERT ON public."cost_categories" TO "authenticated";
GRANT SELECT ON public."cost_categories" TO "authenticated";
GRANT UPDATE ON public."cost_categories" TO "authenticated";
GRANT DELETE ON public."cost_categories" TO "authenticated";
GRANT TRUNCATE ON public."cost_categories" TO "authenticated";
GRANT REFERENCES ON public."cost_categories" TO "authenticated";
GRANT TRIGGER ON public."cost_categories" TO "authenticated";
GRANT INSERT ON public."annual_cost_estimates" TO "authenticated";
GRANT SELECT ON public."annual_cost_estimates" TO "authenticated";
GRANT UPDATE ON public."annual_cost_estimates" TO "authenticated";
GRANT DELETE ON public."annual_cost_estimates" TO "authenticated";
GRANT TRUNCATE ON public."annual_cost_estimates" TO "authenticated";
GRANT REFERENCES ON public."annual_cost_estimates" TO "authenticated";
GRANT TRIGGER ON public."annual_cost_estimates" TO "authenticated";
GRANT INSERT ON public."estimate_monthly_allocations" TO "authenticated";
GRANT SELECT ON public."estimate_monthly_allocations" TO "authenticated";
GRANT UPDATE ON public."estimate_monthly_allocations" TO "authenticated";
GRANT DELETE ON public."estimate_monthly_allocations" TO "authenticated";
GRANT TRUNCATE ON public."estimate_monthly_allocations" TO "authenticated";
GRANT REFERENCES ON public."estimate_monthly_allocations" TO "authenticated";
GRANT TRIGGER ON public."estimate_monthly_allocations" TO "authenticated";
GRANT INSERT ON public."costs" TO "authenticated";
GRANT SELECT ON public."costs" TO "authenticated";
GRANT UPDATE ON public."costs" TO "authenticated";
GRANT DELETE ON public."costs" TO "authenticated";
GRANT TRUNCATE ON public."costs" TO "authenticated";
GRANT REFERENCES ON public."costs" TO "authenticated";
GRANT TRIGGER ON public."costs" TO "authenticated";
GRANT INSERT ON public."contributions" TO "authenticated";
GRANT SELECT ON public."contributions" TO "authenticated";
GRANT UPDATE ON public."contributions" TO "authenticated";
GRANT DELETE ON public."contributions" TO "authenticated";
GRANT TRUNCATE ON public."contributions" TO "authenticated";
GRANT REFERENCES ON public."contributions" TO "authenticated";
GRANT TRIGGER ON public."contributions" TO "authenticated";
GRANT INSERT ON public."tax_deductions" TO "authenticated";
GRANT SELECT ON public."tax_deductions" TO "authenticated";
GRANT UPDATE ON public."tax_deductions" TO "authenticated";
GRANT DELETE ON public."tax_deductions" TO "authenticated";
GRANT TRUNCATE ON public."tax_deductions" TO "authenticated";
GRANT REFERENCES ON public."tax_deductions" TO "authenticated";
GRANT TRIGGER ON public."tax_deductions" TO "authenticated";
GRANT INSERT ON public."tax_credits" TO "authenticated";
GRANT SELECT ON public."tax_credits" TO "authenticated";
GRANT UPDATE ON public."tax_credits" TO "authenticated";
GRANT DELETE ON public."tax_credits" TO "authenticated";
GRANT TRUNCATE ON public."tax_credits" TO "authenticated";
GRANT REFERENCES ON public."tax_credits" TO "authenticated";
GRANT TRIGGER ON public."tax_credits" TO "authenticated";
GRANT INSERT ON public."monthly_reserves" TO "authenticated";
GRANT SELECT ON public."monthly_reserves" TO "authenticated";
GRANT UPDATE ON public."monthly_reserves" TO "authenticated";
GRANT DELETE ON public."monthly_reserves" TO "authenticated";
GRANT TRUNCATE ON public."monthly_reserves" TO "authenticated";
GRANT REFERENCES ON public."monthly_reserves" TO "authenticated";
GRANT TRIGGER ON public."monthly_reserves" TO "authenticated";
GRANT INSERT ON public."vat_adjustments" TO "authenticated";
GRANT SELECT ON public."vat_adjustments" TO "authenticated";
GRANT UPDATE ON public."vat_adjustments" TO "authenticated";
GRANT DELETE ON public."vat_adjustments" TO "authenticated";
GRANT TRUNCATE ON public."vat_adjustments" TO "authenticated";
GRANT REFERENCES ON public."vat_adjustments" TO "authenticated";
GRANT TRIGGER ON public."vat_adjustments" TO "authenticated";
GRANT INSERT ON public."monthly_net_commissions" TO "authenticated";
GRANT SELECT ON public."monthly_net_commissions" TO "authenticated";
GRANT UPDATE ON public."monthly_net_commissions" TO "authenticated";
GRANT DELETE ON public."monthly_net_commissions" TO "authenticated";
GRANT TRUNCATE ON public."monthly_net_commissions" TO "authenticated";
GRANT REFERENCES ON public."monthly_net_commissions" TO "authenticated";
GRANT TRIGGER ON public."monthly_net_commissions" TO "authenticated";
GRANT INSERT ON public."depreciable_assets" TO "authenticated";
GRANT SELECT ON public."depreciable_assets" TO "authenticated";
GRANT UPDATE ON public."depreciable_assets" TO "authenticated";
GRANT DELETE ON public."depreciable_assets" TO "authenticated";
GRANT INSERT ON public."purchase_vat_invoices" TO "authenticated";
GRANT SELECT ON public."purchase_vat_invoices" TO "authenticated";
GRANT UPDATE ON public."purchase_vat_invoices" TO "authenticated";
GRANT DELETE ON public."purchase_vat_invoices" TO "authenticated";
GRANT INSERT ON public."sales_vat_invoices" TO "authenticated";
GRANT SELECT ON public."sales_vat_invoices" TO "authenticated";
GRANT UPDATE ON public."sales_vat_invoices" TO "authenticated";
GRANT DELETE ON public."sales_vat_invoices" TO "authenticated";
GRANT INSERT ON public."vat_periods" TO "authenticated";
GRANT SELECT ON public."vat_periods" TO "authenticated";
GRANT UPDATE ON public."vat_periods" TO "authenticated";
GRANT DELETE ON public."vat_periods" TO "authenticated";
GRANT INSERT ON public."pension_payments" TO "authenticated";
GRANT SELECT ON public."pension_payments" TO "authenticated";
GRANT UPDATE ON public."pension_payments" TO "authenticated";
GRANT DELETE ON public."pension_payments" TO "authenticated";
GRANT INSERT ON public."purchase_cost_links" TO "authenticated";
GRANT SELECT ON public."purchase_cost_links" TO "authenticated";
GRANT UPDATE ON public."purchase_cost_links" TO "authenticated";
GRANT DELETE ON public."purchase_cost_links" TO "authenticated";
REVOKE ALL ON FUNCTION public.piva_validate_depreciable_asset() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.piva_validate_fiscal_year_status() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.piva_validate_structure_record() FROM PUBLIC,anon,authenticated;
REVOKE ALL ON FUNCTION public.piva_import_invoice(jsonb) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.piva_import_invoice(jsonb) TO authenticated;
COMMIT;
