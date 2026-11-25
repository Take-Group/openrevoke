// Personal API tokens and the MCP server address (`/api/api-tokens`, panel session only).

export type ApiTokenScope = "read" | "write";

export interface ApiTokenOut {
  id: string;
  name: string;
  /** First characters of the token, to tell tokens apart. */
  prefix: string;
  scope: ApiTokenScope;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiTokenList {
  items: ApiTokenOut[];
  /** Address of the MCP server for AI assistants. */
  mcp_url: string;
}

export interface ApiTokenCreate {
  name: string;
  scope: ApiTokenScope;
}

export interface ApiTokenCreated {
  token: ApiTokenOut;
  /** The token itself: returned only once. */
  secret: string;
  mcp_url: string;
}
