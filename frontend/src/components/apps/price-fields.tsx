"use client";

import { BILLING_OPTIONS, PRICING_OPTIONS } from "@/components/apps/app-options";
import { CurrencySelect } from "@/components/common/currency-select";
import { FormField } from "@/components/common/form-field";
import { Segmented } from "@/components/common/segmented";
import { Input } from "@/components/ui/input";
import { OptionSelect } from "@/components/common/option-select";
import type { BillingPeriod, PriceIn, PriceOut, PricingModel } from "@/lib/api/types";

export interface PriceForm {
  pricing_model: PricingModel;
  amount: string;
  currency: string;
  billing_period: BillingPeriod;
}

export const DEFAULT_CURRENCY = "PLN";

export function priceFormFrom(model: PricingModel, price: PriceOut | null): PriceForm {
  return {
    pricing_model: model,
    amount: price?.amount ?? "",
    currency: price?.currency ?? DEFAULT_CURRENCY,
    billing_period: price?.billing_period ?? "monthly",
  };
}

/** The API wants no price for free apps and a price for the others. */
export function priceFromForm(form: PriceForm): PriceIn | null {
  if (form.pricing_model === "free") return null;
  return {
    amount: form.amount.trim().replace(",", "."),
    currency: form.currency.trim().toUpperCase(),
    billing_period: form.billing_period,
  };
}

interface PriceFieldsProps {
  value: PriceForm;
  onChange: (value: PriceForm) => void;
  idPrefix: string;
}

export function PriceFields({ value, onChange, idPrefix }: PriceFieldsProps) {
  const set = <K extends keyof PriceForm>(field: K, fieldValue: PriceForm[K]) => onChange({ ...value, [field]: fieldValue });
  const paid = value.pricing_model !== "free";

  return (
    <div className="flex flex-col gap-4">
      <FormField label="Pricing" info="Per seat: price times active seats. Flat: one price for the whole plan.">
        <Segmented
          label="Pricing"
          value={value.pricing_model}
          onChange={(model) => set("pricing_model", model)}
          options={PRICING_OPTIONS}
          className="w-full [&>*]:flex-1"
        />
      </FormField>
      {paid && (
        <div className="grid grid-cols-[1fr_5.5rem_7.5rem] gap-3">
          <FormField
            label={value.pricing_model === "per_seat" ? "Price per seat" : "Plan price"}
            htmlFor={`${idPrefix}-amount`}
            required
          >
            <Input
              id={`${idPrefix}-amount`}
              required
              inputMode="decimal"
              pattern="^\d{1,10}([.,]\d{1,2})?$"
              placeholder="0.00"
              className="tabular-nums"
              value={value.amount}
              onChange={(event) => set("amount", event.target.value)}
            />
          </FormField>
          <FormField label="Currency" htmlFor={`${idPrefix}-currency`} required>
            <CurrencySelect id={`${idPrefix}-currency`} value={value.currency} onChange={(code) => set("currency", code)} />
          </FormField>
          <FormField label="Billing" htmlFor={`${idPrefix}-period`}>
            <OptionSelect
              id={`${idPrefix}-period`}
              options={BILLING_OPTIONS}
              value={value.billing_period}
              onChange={(next) => next && set("billing_period", next as BillingPeriod)}
            />
          </FormField>
        </div>
      )}
    </div>
  );
}
