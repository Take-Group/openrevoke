"use client";

import { useState } from "react";

import { CodeBlock } from "@/components/common/code-block";
import { Segmented } from "@/components/common/segmented";

type Client = "claude" | "codex" | "json";

const CLIENTS: { value: Client; label: string }[] = [
  { value: "claude", label: "Claude Code" },
  { value: "codex", label: "Codex" },
  { value: "json", label: "Cursor and others" },
];

const PLACEHOLDER = "<your token>";

function snippet(client: Client, url: string, token: string): { hint: string; code: string } {
  if (client === "claude") {
    return {
      hint: "Run in a terminal. --scope user makes it available in every project.",
      code: `claude mcp add --transport http --scope user open-revoke ${url} \\\n  --header "Authorization: Bearer ${token}"`,
    };
  }
  if (client === "codex") {
    return {
      hint: "Add to ~/.codex/config.toml and set the variable in your shell profile.",
      code: `[mcp_servers.open-revoke]\nurl = "${url}"\nbearer_token_env_var = "OPEN_REVOKE_TOKEN"\n\n# in ~/.zshrc or ~/.bashrc\nexport OPEN_REVOKE_TOKEN="${token}"`,
    };
  }
  const config = { mcpServers: { "open-revoke": { url, headers: { Authorization: `Bearer ${token}` } } } };
  return {
    hint: "Cursor: ~/.cursor/mcp.json. Other clients that speak Streamable HTTP take the same URL and header.",
    code: JSON.stringify(config, null, 2),
  };
}

/** How to connect an AI assistant to the MCP server; with `token` the snippets are ready to paste. */
export function McpSetupGuide({ url, token }: { url: string; token?: string }) {
  const [client, setClient] = useState<Client>("claude");
  const { hint, code } = snippet(client, url, token ?? PLACEHOLDER);
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <Segmented label="AI assistant" value={client} onChange={setClient} options={CLIENTS} className="self-start" />
      <p className="text-sm text-muted-foreground">{hint}</p>
      <CodeBlock code={code} label="the configuration" />
    </div>
  );
}
