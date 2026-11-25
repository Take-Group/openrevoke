/** Types of the Slack bot setup (/api/slack-agent), from docs/openapi.json. */

import type { DateTimeString } from "@/lib/api/types";

export type SlackAgentStatus = "not_configured" | "disabled" | "connecting" | "connected" | "error";

export interface SlackAgentOut {
  status: SlackAgentStatus;
  enabled: boolean;
  bot_name: string | null;
  app_id: string | null;
  team_name: string | null;
  bot_user_id: string | null;
  has_bot_token: boolean;
  has_app_token: boolean;
  /** An app configuration token is saved: the icon can be changed. */
  has_config_token: boolean;
  avatar_set_at: DateTimeString | null;
  avatar_error: string | null;
  last_error: string | null;
  connected_at: DateTimeString | null;
  ai_configured: boolean;
  /** Where the admin installs the app; with oauth_install it comes back and saves the bot token. */
  install_url: string | null;
  oauth_install: boolean;
  app_settings_url: string | null;
  /** Basic Information page with App-Level Tokens. */
  app_token_url: string | null;
  /** Creates the app from the manifest by hand. */
  manifest_url: string;
}

export interface SlackAppCreate {
  config_token: string;
  config_refresh_token?: string | null;
  bot_name: string;
}

export interface SlackTokensUpdate {
  bot_token?: string | null;
  app_token?: string | null;
}
