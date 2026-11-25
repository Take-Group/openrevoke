"use client";

import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { AlertsList } from "@/components/dashboard/alerts-list";
import { AppsByCost } from "@/components/dashboard/apps-by-cost";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { SetupChecklist } from "@/components/dashboard/setup-checklist";
import { useDashboard } from "@/hooks/use-dashboard";

export function DashboardView() {
  const query = useDashboard();
  return (
    <>
      <PageHeader title="Dashboard" />
      <SetupChecklist />
      <QueryState query={query} rows={6}>
        {(data) => (
          <div className="flex flex-col gap-6">
            <KpiCards data={data} />
            <div className="grid items-stretch gap-6 lg:grid-cols-5">
              <div className="min-w-0 lg:col-span-3">
                <AlertsList alerts={data.alerts} />
              </div>
              <div className="min-w-0 lg:col-span-2">
                <AppsByCost totals={data.monthly_cost} total={data.monthly_cost_total} />
              </div>
            </div>
          </div>
        )}
      </QueryState>
    </>
  );
}
