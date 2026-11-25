import {
  si1password,
  siAirtable,
  siAnthropic,
  siAsana,
  siAtlassian,
  siBitbucket,
  siBitwarden,
  siCalendly,
  siClaude,
  siClickup,
  siCloudflare,
  siConfluence,
  siCursor,
  siDeepl,
  siDiscord,
  siDocker,
  siDropbox,
  siFigma,
  siFramer,
  siGithub,
  siGitlab,
  siGooglegemini,
  siGrammarly,
  siHubspot,
  siIntercom,
  siJira,
  siLinear,
  siLoom,
  siMailchimp,
  siMake,
  siMiro,
  siN8n,
  siNetlify,
  siNotion,
  siPerplexity,
  siPostman,
  siSemrush,
  siSentry,
  siShopify,
  siSketch,
  siStripe,
  siSupabase,
  siTelegram,
  siTrello,
  siVercel,
  siWebflow,
  siZapier,
  siZendesk,
  siZoom,
  type SimpleIcon,
} from "simple-icons";

/** One-colour mark (a simple-icons icon) or a mark in several colours. */
export type BrandIcon = Pick<SimpleIcon, "path" | "hex"> | { parts: Pick<SimpleIcon, "path" | "hex">[] };

/**
 * Brand marks bundled with the panel (simple-icons, CC0), so the panel never
 * asks a third party for a favicon. Brands that are not in simple-icons
 * (OpenAI) get a tile in their colour with initials.
 */
export type Brand = { icon: BrandIcon } | { color: string };

/*
 * Slack, Microsoft and Microsoft Teams left simple-icons at the brands' request; these paths are
 * from simple-icons 9.0.0 (CC0), coloured as the brands' own logos. Used only to name the product.
 */
const SLACK: BrandIcon = {
  parts: [
      { path: "M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z", hex: "E01E5A" },
      { path: "M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z", hex: "36C5F0" },
      { path: "M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z", hex: "2EB67D" },
      { path: "M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z", hex: "ECB22E" },
  ],
};
const MICROSOFT: BrandIcon = {
  parts: [
    { path: "M0 0v11.408h11.408V0z", hex: "F25022" },
    { path: "M12.594 0v11.408H24V0z", hex: "7FBA00" },
    { path: "M0 12.594V24h11.408V12.594z", hex: "00A4EF" },
    { path: "M12.594 12.594V24H24V12.594z", hex: "FFB900" },
  ],
};
/*
 * Google's "G" in its four brand colours (simple-icons ships it in one colour), on a 24x24 grid.
 * Used only to name the product.
 */
const GOOGLE: BrandIcon = {
  parts: [
    { path: "M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z", hex: "4285F4" },
    { path: "M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z", hex: "34A853" },
    { path: "M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z", hex: "FBBC05" },
    { path: "M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z", hex: "EA4335" },
  ],
};
const MICROSOFT_TEAMS: BrandIcon = {
  hex: "6264A7",
  path: "M20.625 8.127q-.55 0-1.025-.205-.475-.205-.832-.563-.358-.357-.563-.832Q18 6.053 18 5.502q0-.54.205-1.02t.563-.837q.357-.358.832-.563.474-.205 1.025-.205.54 0 1.02.205t.837.563q.358.357.563.837.205.48.205 1.02 0 .55-.205 1.025-.205.475-.563.832-.357.358-.837.563-.48.205-1.02.205zm0-3.75q-.469 0-.797.328-.328.328-.328.797 0 .469.328.797.328.328.797.328.469 0 .797-.328.328-.328.328-.797 0-.469-.328-.797-.328-.328-.797-.328zM24 10.002v5.578q0 .774-.293 1.46-.293.685-.803 1.194-.51.51-1.195.803-.686.293-1.459.293-.445 0-.908-.105-.463-.106-.85-.329-.293.95-.855 1.729-.563.78-1.319 1.336-.756.557-1.67.861-.914.305-1.898.305-1.148 0-2.162-.398-1.014-.399-1.805-1.102-.79-.703-1.312-1.664t-.674-2.086h-5.8q-.411 0-.704-.293T0 16.881V6.873q0-.41.293-.703t.703-.293h8.59q-.34-.715-.34-1.5 0-.727.275-1.365.276-.639.75-1.114.475-.474 1.114-.75.638-.275 1.365-.275t1.365.275q.639.276 1.114.75.474.475.75 1.114.275.638.275 1.365t-.275 1.365q-.276.639-.75 1.113-.475.475-1.114.75-.638.276-1.365.276-.188 0-.375-.024-.188-.023-.375-.058v1.078h10.875q.469 0 .797.328.328.328.328.797zM12.75 2.373q-.41 0-.78.158-.368.158-.638.434-.27.275-.428.639-.158.363-.158.773 0 .41.158.78.159.368.428.638.27.27.639.428.369.158.779.158.41 0 .773-.158.364-.159.64-.428.274-.27.433-.639.158-.369.158-.779 0-.41-.158-.773-.159-.364-.434-.64-.275-.275-.639-.433-.363-.158-.773-.158zM6.937 9.814h2.25V7.94H2.814v1.875h2.25v6h1.875zm10.313 7.313v-6.75H12v6.504q0 .41-.293.703t-.703.293H8.309q.152.809.556 1.5.405.691.985 1.19.58.497 1.318.779.738.281 1.582.281.926 0 1.746-.352.82-.351 1.436-.966.615-.616.966-1.43.352-.815.352-1.752zm5.25-1.547v-5.203h-3.75v6.855q.305.305.691.452.387.146.809.146.469 0 .879-.176.41-.175.715-.48.304-.305.48-.715t.176-.879Z",
};

const BRANDS: Record<string, Brand> = {
  googleworkspace: { icon: GOOGLE },
  google: { icon: GOOGLE },
  gmail: { icon: GOOGLE },
  github: { icon: siGithub },
  gitlab: { icon: siGitlab },
  bitbucket: { icon: siBitbucket },
  claude: { icon: siClaude },
  claudeteam: { icon: siClaude },
  anthropic: { icon: siAnthropic },
  gemini: { icon: siGooglegemini },
  slack: { icon: SLACK },
  microsoft: { icon: MICROSOFT },
  microsoft365: { icon: MICROSOFT },
  office365: { icon: MICROSOFT },
  microsoftteams: { icon: MICROSOFT_TEAMS },
  teams: { icon: MICROSOFT_TEAMS },
  chatgpt: { color: "#10A37F" },
  openai: { color: "#10A37F" },
  notion: { icon: siNotion },
  figma: { icon: siFigma },
  jira: { icon: siJira },
  confluence: { icon: siConfluence },
  atlassian: { icon: siAtlassian },
  linear: { icon: siLinear },
  zoom: { icon: siZoom },
  dropbox: { icon: siDropbox },
  miro: { icon: siMiro },
  hubspot: { icon: siHubspot },
  asana: { icon: siAsana },
  trello: { icon: siTrello },
  clickup: { icon: siClickup },
  vercel: { icon: siVercel },
  cloudflare: { icon: siCloudflare },
  docker: { icon: siDocker },
  postman: { icon: siPostman },
  semrush: { icon: siSemrush },
  "1password": { icon: si1password },
  bitwarden: { icon: siBitwarden },
  loom: { icon: siLoom },
  calendly: { icon: siCalendly },
  intercom: { icon: siIntercom },
  zendesk: { icon: siZendesk },
  mailchimp: { icon: siMailchimp },
  airtable: { icon: siAirtable },
  discord: { icon: siDiscord },
  sentry: { icon: siSentry },
  netlify: { icon: siNetlify },
  supabase: { icon: siSupabase },
  cursor: { icon: siCursor },
  perplexity: { icon: siPerplexity },
  deepl: { icon: siDeepl },
  grammarly: { icon: siGrammarly },
  sketch: { icon: siSketch },
  webflow: { icon: siWebflow },
  framer: { icon: siFramer },
  shopify: { icon: siShopify },
  stripe: { icon: siStripe },
  telegram: { icon: siTelegram },
  zapier: { icon: siZapier },
  make: { icon: siMake },
  n8n: { icon: siN8n },
};

/** Lowercase letters and digits only; the API's app catalog keys use the same rule. */
export function normalizeName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** Brand by connector key first, then by the app's slug or name. */
export function findBrand(...candidates: (string | null | undefined)[]): Brand | null {
  for (const candidate of candidates) {
    if (!candidate) continue;
    const brand = BRANDS[normalizeName(candidate)];
    if (brand) return brand;
  }
  return null;
}

/** Relative luminance of "#RRGGBB" or "RRGGBB", 0 (black) to 1 (white). */
export function luminance(hex: string): number {
  const value = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => {
    const channel = parseInt(value.slice(i, i + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
