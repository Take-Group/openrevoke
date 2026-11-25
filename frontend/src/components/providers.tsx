"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api/client";

function makeQueryClient() {
  // A 401 anywhere means the session ended: refresh the auth state, the gate then shows sign-in.
  // Sign-in steps (meta.authFlow) answer 401 for a wrong password or code; that is not a lost session.
  const onError = (error: unknown, meta?: Record<string, unknown>) => {
    if (meta?.authFlow || !(error instanceof ApiError) || !error.unauthorized) return;
    if (!client.isFetching({ queryKey: ["auth"] })) void client.invalidateQueries({ queryKey: ["auth"] });
  };
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: (error, query) => onError(error, query.meta) }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _onMutateResult, mutation) => onError(error, mutation.meta),
    }),
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        refetchOnWindowFocus: true,
        // Client errors (404, 422, 501) do not get better with a retry.
        retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 502) && count < 2,
      },
    },
  });
  return client;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delay={300}>
          {children}
          <Toaster position="bottom-right" closeButton />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
