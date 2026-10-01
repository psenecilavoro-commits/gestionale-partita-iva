-- Schema-only clone of Personale; synthetic staging only.
BEGIN;
CREATE TABLE public."annual_cost_estimates" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"category_id" uuid NOT NULL,
"estimated_gross_amount" numeric(14,2) DEFAULT 0 NOT NULL,
"amount_includes_vat" boolean DEFAULT true NOT NULL,
"notes" text
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
CREATE TABLE public."estimate_monthly_allocations" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"estimate_id" uuid NOT NULL,
"month" smallint NOT NULL,
"planned_gross_amount" numeric(14,2) NOT NULL
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
CREATE TABLE public."fiscal_years" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year" integer NOT NULL,
"status" text DEFAULT 'open'::text NOT NULL,
"notes" text,
"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE public."monthly_net_commissions" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"month" integer NOT NULL,
"amount" numeric(14,2) NOT NULL
);
CREATE TABLE public."monthly_reserves" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"month" smallint NOT NULL,
"reserved_amount" numeric(14,2) DEFAULT 0 NOT NULL,
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
CREATE TABLE public."vehicle_monthly" (
"id" uuid DEFAULT gen_random_uuid() NOT NULL,
"user_id" uuid DEFAULT auth.uid() NOT NULL,
"fiscal_year_id" uuid NOT NULL,
"vehicle_id" uuid NOT NULL,
"month" smallint NOT NULL,
"distance_km" numeric(12,2) NOT NULL,
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
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_fiscal_year_check" CHECK (((fiscal_year >= 2000) AND (fiscal_year <= 2100)));
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_pkey" PRIMARY KEY (id);
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_status_check" CHECK ((status = ANY (ARRAY['open'::text, 'closed'::text])));
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_user_id_fiscal_year_key" UNIQUE (user_id, fiscal_year);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_check" CHECK (((unit <> 'RATE'::text) OR ((value >= (0)::numeric) AND (value <= (2)::numeric))));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_code_check" CHECK (((length(TRIM(BOTH FROM code)) >= 1) AND (length(TRIM(BOTH FROM code)) <= 100)));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_pkey" PRIMARY KEY (id);
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_unit_check" CHECK ((unit = ANY (ARRAY['EUR'::text, 'RATE'::text, 'KM'::text, 'EUR_PER_KM'::text, 'COUNT'::text])));
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_user_id_fiscal_year_id_code_key" UNIQUE (user_id, fiscal_year_id, code);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_pkey" PRIMARY KEY (id);
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_projection_mode_check" CHECK ((projection_mode = ANY (ARRAY['observed_months'::text, 'calendar_months'::text])));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_target_revenue_1_check" CHECK ((target_revenue_1 >= (0)::numeric));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_target_revenue_2_check" CHECK ((target_revenue_2 >= (0)::numeric));
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_user_id_fiscal_year_id_key" UNIQUE (user_id, fiscal_year_id);
ALTER TABLE public."principals" ADD CONSTRAINT "principals_check" CHECK (((end_date IS NULL) OR (start_date IS NULL) OR (end_date >= start_date)));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_enasarco_relationship_check" CHECK ((enasarco_relationship = ANY (ARRAY['plurimandatario'::text, 'monomandatario'::text])));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."principals" ADD CONSTRAINT "principals_name_check" CHECK ((length(TRIM(BOTH FROM name)) > 0));
ALTER TABLE public."principals" ADD CONSTRAINT "principals_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_user_id_fiscal_year_id_principal_id_month_key" UNIQUE (user_id, fiscal_year_id, principal_id, month);
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_acquisition_cost_gross_check" CHECK ((acquisition_cost_gross >= (0)::numeric));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_check" CHECK (((contract_end IS NULL) OR (contract_start IS NULL) OR (contract_end >= contract_start)));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_label_check" CHECK ((length(TRIM(BOTH FROM label)) > 0));
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_annual_km_limit_check" CHECK ((annual_km_limit >= 0));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_excess_km_penalty_check" CHECK ((excess_km_penalty >= (0)::numeric));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_fiscal_cost_limit_check" CHECK ((fiscal_cost_limit >= (0)::numeric));
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_user_id_fiscal_year_id_vehicle_id_key" UNIQUE (user_id, fiscal_year_id, vehicle_id);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_distance_km_check" CHECK ((distance_km >= (0)::numeric));
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_pkey" PRIMARY KEY (id);
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_user_id_fiscal_year_id_vehicle_id_month_key" UNIQUE (user_id, fiscal_year_id, vehicle_id, month);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_code_check" CHECK (((length(TRIM(BOTH FROM code)) >= 1) AND (length(TRIM(BOTH FROM code)) <= 80)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_cost_deductible_rate_check" CHECK (((cost_deductible_rate >= (0)::numeric) AND (cost_deductible_rate <= (1)::numeric)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_id_user_id_fiscal_year_id_key" UNIQUE (id, user_id, fiscal_year_id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_name_check" CHECK ((length(TRIM(BOTH FROM name)) > 0));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_pkey" PRIMARY KEY (id);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_user_id_fiscal_year_id_code_key" UNIQUE (user_id, fiscal_year_id, code);
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_vat_deductible_rate_check" CHECK (((vat_deductible_rate >= (0)::numeric) AND (vat_deductible_rate <= (1)::numeric)));
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_vat_rate_check" CHECK (((vat_rate >= (0)::numeric) AND (vat_rate <= (1)::numeric)));
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_estimated_gross_amount_check" CHECK ((estimated_gross_amount >= (0)::numeric));
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_id_user_id_fiscal_year_id_key" UNIQUE (id, user_id, fiscal_year_id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_pkey" PRIMARY KEY (id);
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_user_id_fiscal_year_id_category_id_key" UNIQUE (user_id, fiscal_year_id, category_id);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_pkey" PRIMARY KEY (id);
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_planned_gross_amount_check" CHECK ((planned_gross_amount >= (0)::numeric));
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_user_id_estimate_id_month_key" UNIQUE (user_id, estimate_id, month);
ALTER TABLE public."costs" ADD CONSTRAINT "costs_cost_deductible_rate_check" CHECK (((cost_deductible_rate >= (0)::numeric) AND (cost_deductible_rate <= (1)::numeric)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_fiscal_competence_year_check" CHECK (((fiscal_competence_year >= 2000) AND (fiscal_competence_year <= 2100)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_gross_amount_check" CHECK ((gross_amount >= (0)::numeric));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."costs" ADD CONSTRAINT "costs_pkey" PRIMARY KEY (id);
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vat_deductible_rate_check" CHECK (((vat_deductible_rate >= (0)::numeric) AND (vat_deductible_rate <= (1)::numeric)));
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vat_rate_check" CHECK (((vat_rate >= (0)::numeric) AND (vat_rate <= (1)::numeric)));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_check" CHECK ((deductible_amount <= amount));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_competence_year_check" CHECK (((competence_year >= 2000) AND (competence_year <= 2100)));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_contribution_type_check" CHECK ((contribution_type = ANY (ARRAY['inps_fixed'::text, 'inps_excess'::text, 'enasarco'::text, 'other'::text])));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_deductible_amount_check" CHECK ((deductible_amount >= (0)::numeric));
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_pkey" PRIMARY KEY (id);
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_deductible_limit_check" CHECK ((deductible_limit >= (0)::numeric));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_pkey" PRIMARY KEY (id);
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_credit_rate_check" CHECK (((credit_rate >= (0)::numeric) AND (credit_rate <= (2)::numeric)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_first_fiscal_year_check" CHECK (((first_fiscal_year >= 2000) AND (first_fiscal_year <= 2100)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_installment_count_check" CHECK (((installment_count >= 1) AND (installment_count <= 30)));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_original_amount_check" CHECK ((original_amount >= (0)::numeric));
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_reserved_amount_check" CHECK ((reserved_amount >= (0)::numeric));
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_user_id_fiscal_year_id_month_key" UNIQUE (user_id, fiscal_year_id, month);
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_description_check" CHECK ((length(TRIM(BOTH FROM description)) > 0));
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_id_user_id_key" UNIQUE (id, user_id);
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_pkey" PRIMARY KEY (id);
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_amount_check" CHECK ((amount >= (0)::numeric));
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_fiscal_year_id_month_key" UNIQUE (fiscal_year_id, month);
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_month_check" CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_pkey" PRIMARY KEY (id);
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_check" CHECK (((deductible_vat >= (0)::numeric) AND (deductible_vat <= gross_amount)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_depreciation_rate_check" CHECK (((depreciation_rate > (0)::numeric) AND (depreciation_rate <= (1)::numeric)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_description_check" CHECK (((length(btrim(description)) >= 1) AND (length(btrim(description)) <= 200)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_first_fiscal_year_check" CHECK (((first_fiscal_year >= 2000) AND (first_fiscal_year <= 2100)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_gross_amount_check" CHECK ((gross_amount >= (0)::numeric));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_notes_check" CHECK (((notes IS NULL) OR (length(notes) <= 500)));
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_pkey" PRIMARY KEY (id);
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_purchase_date_status_check" CHECK ((is_planned OR (purchase_date <= CURRENT_DATE)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_category_check" CHECK ((category = ANY (ARRAY['auto'::text, 'altro'::text])));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check" CHECK (((deductible_vat >= (0)::numeric) AND (deductible_vat <= vat_amount)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check1" CHECK ((received_date >= operation_date));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_check2" CHECK ((registered_date >= received_date));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_invoice_number_check" CHECK (((length(btrim(invoice_number)) >= 1) AND (length(btrim(invoice_number)) <= 100)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_notes_check" CHECK (((notes IS NULL) OR (length(notes) <= 500)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_pkey" PRIMARY KEY (id);
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_supplier_check" CHECK (((length(btrim(supplier)) >= 1) AND (length(btrim(supplier)) <= 200)));
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_vat_amount_check" CHECK ((vat_amount >= (0)::numeric));
ALTER TABLE public."fiscal_years" ADD CONSTRAINT "fiscal_years_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."fiscal_parameters" ADD CONSTRAINT "fiscal_parameters_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."annual_settings" ADD CONSTRAINT "annual_settings_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."principals" ADD CONSTRAINT "principals_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_principal_id_user_id_fkey" FOREIGN KEY (principal_id, user_id) REFERENCES principals(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."monthly_revenues" ADD CONSTRAINT "monthly_revenues_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicles" ADD CONSTRAINT "vehicles_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_year_settings" ADD CONSTRAINT "vehicle_year_settings_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vehicle_monthly" ADD CONSTRAINT "vehicle_monthly_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."cost_categories" ADD CONSTRAINT "cost_categories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_category_id_user_id_fiscal_year_id_fkey" FOREIGN KEY (category_id, user_id, fiscal_year_id) REFERENCES cost_categories(id, user_id, fiscal_year_id) ON DELETE RESTRICT;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."annual_cost_estimates" ADD CONSTRAINT "annual_cost_estimates_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_estimate_id_user_id_fiscal_ye_fkey" FOREIGN KEY (estimate_id, user_id, fiscal_year_id) REFERENCES annual_cost_estimates(id, user_id, fiscal_year_id) ON DELETE CASCADE;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."estimate_monthly_allocations" ADD CONSTRAINT "estimate_monthly_allocations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_category_id_user_id_fiscal_year_id_fkey" FOREIGN KEY (category_id, user_id, fiscal_year_id) REFERENCES cost_categories(id, user_id, fiscal_year_id) ON DELETE RESTRICT;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."costs" ADD CONSTRAINT "costs_vehicle_id_user_id_fkey" FOREIGN KEY (vehicle_id, user_id) REFERENCES vehicles(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."contributions" ADD CONSTRAINT "contributions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."tax_deductions" ADD CONSTRAINT "tax_deductions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."tax_credits" ADD CONSTRAINT "tax_credits_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."monthly_reserves" ADD CONSTRAINT "monthly_reserves_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_fiscal_year_id_user_id_fkey" FOREIGN KEY (fiscal_year_id, user_id) REFERENCES fiscal_years(id, user_id) ON DELETE RESTRICT;
ALTER TABLE public."vat_adjustments" ADD CONSTRAINT "vat_adjustments_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public."monthly_net_commissions" ADD CONSTRAINT "monthly_net_commissions_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."depreciable_assets" ADD CONSTRAINT "depreciable_assets_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
ALTER TABLE public."purchase_vat_invoices" ADD CONSTRAINT "purchase_vat_invoices_fiscal_year_id_fkey" FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT;
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
CREATE TRIGGER piva_validate_depreciable_asset BEFORE INSERT OR UPDATE ON public.depreciable_assets FOR EACH ROW EXECUTE FUNCTION piva_validate_depreciable_asset();
CREATE TRIGGER piva_validate_fiscal_year_status BEFORE UPDATE ON public.fiscal_years FOR EACH ROW EXECUTE FUNCTION piva_validate_fiscal_year_status();
ALTER TABLE public."annual_cost_estimates" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."annual_settings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."contributions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."cost_categories" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."costs" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."depreciable_assets" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."estimate_monthly_allocations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."fiscal_parameters" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."fiscal_years" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."monthly_net_commissions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."monthly_reserves" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."monthly_revenues" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."principals" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."purchase_vat_invoices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."tax_credits" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."tax_deductions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."vat_adjustments" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."vehicle_monthly" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."vehicle_year_settings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."vehicles" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "owner_select" ON public."fiscal_years" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."fiscal_years" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."fiscal_years" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."fiscal_years" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."fiscal_parameters" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."fiscal_parameters" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."fiscal_parameters" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."fiscal_parameters" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."annual_settings" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."annual_settings" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."annual_settings" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."annual_settings" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."principals" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."principals" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "net_commissions_delete_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."principals" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."principals" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."monthly_revenues" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."monthly_revenues" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "purchase_vat_select_owner" ON public."purchase_vat_invoices" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "owner_update" ON public."monthly_revenues" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."monthly_revenues" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicles" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicles" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "purchase_vat_insert_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."vehicles" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicles" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicle_year_settings" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicle_year_settings" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "purchase_vat_update_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."vehicle_year_settings" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicle_year_settings" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vehicle_monthly" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vehicle_monthly" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "purchase_vat_delete_owner_open" ON public."purchase_vat_invoices" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = purchase_vat_invoices.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."vehicle_monthly" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vehicle_monthly" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."cost_categories" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."cost_categories" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."cost_categories" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."cost_categories" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."annual_cost_estimates" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."annual_cost_estimates" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."annual_cost_estimates" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."annual_cost_estimates" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."estimate_monthly_allocations" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."costs" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."costs" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."costs" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."costs" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."contributions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."contributions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_depreciable_read" ON public."depreciable_assets" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "owner_update" ON public."contributions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."contributions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."tax_deductions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."tax_deductions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_depreciable_insert" ON public."depreciable_assets" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."tax_deductions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."tax_deductions" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."tax_credits" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."tax_credits" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_depreciable_update" ON public."depreciable_assets" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."tax_credits" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."tax_credits" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."monthly_reserves" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."monthly_reserves" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_depreciable_delete" ON public."depreciable_assets" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years f
  WHERE ((f.id = depreciable_assets.fiscal_year_id) AND (f.user_id = ( SELECT auth.uid() AS uid)) AND (f.status = 'open'::text)))));
CREATE POLICY "owner_update" ON public."monthly_reserves" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."monthly_reserves" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_select" ON public."vat_adjustments" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_insert" ON public."vat_adjustments" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_update" ON public."vat_adjustments" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "owner_delete" ON public."vat_adjustments" AS PERMISSIVE FOR DELETE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "net_commissions_select_owner" ON public."monthly_net_commissions" AS PERMISSIVE FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid))))));
CREATE POLICY "net_commissions_insert_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "net_commissions_update_owner_open" ON public."monthly_net_commissions" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM fiscal_years fy
  WHERE ((fy.id = monthly_net_commissions.fiscal_year_id) AND (fy.user_id = ( SELECT auth.uid() AS uid)) AND (fy.status = 'open'::text)))));
CREATE POLICY "piva_fiscal_year_update_owner" ON public."fiscal_years" AS PERMISSIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
CREATE POLICY "piva_fiscal_year_update_owner_guard" ON public."fiscal_years" AS RESTRICTIVE FOR UPDATE TO "authenticated" USING ((user_id = ( SELECT auth.uid() AS uid))) WITH CHECK ((user_id = ( SELECT auth.uid() AS uid)));
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."annual_cost_estimates" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."annual_settings" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."contributions" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."cost_categories" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."costs" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."depreciable_assets" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."estimate_monthly_allocations" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."fiscal_parameters" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."fiscal_years" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."monthly_net_commissions" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."monthly_reserves" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."monthly_revenues" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."principals" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."purchase_vat_invoices" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."tax_credits" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."tax_deductions" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."vat_adjustments" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."vehicle_monthly" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."vehicle_year_settings" TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public."vehicles" TO authenticated;
COMMIT;
