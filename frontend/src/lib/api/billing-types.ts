import type { BillingPeriod, PricingModel } from "@/lib/api/types";

/** What the app's own billing reports, read by the sync (`AppDetail.billing`). */
export interface AppBillingOut {
  plan: string | null;
  pricing_model: PricingModel;
  /** Per billed seat (per_seat) or for the whole plan (flat), per period. */
  unit_amount: string;
  currency: string;
  billing_period: BillingPeriod;
  /** Seats the app bills now, when it says. */
  billed_seats: number | null;
  /** What the app bills per period now, when it says. */
  total_amount: string | null;
  renews_on: string | null;
  /** The app's price follows this billing; false after a manual price. */
  applies_to_price: boolean;
  read_at: string;
}
