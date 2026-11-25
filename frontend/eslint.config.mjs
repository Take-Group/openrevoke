import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// UI kit rules (skills/frontend/ui-kit.md). The messages tell the agent which component to use.
const KIT = "Read open-revoke/skills/frontend/ui-kit.md.";

const PALETTE =
  "(?:bg|text|border|ring|fill|stroke|from|to|via|outline|decoration|divide|shadow|accent|caret)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\\d{2,3}";

// Everywhere, kit included: colours are tokens, interactive things never get the arrow cursor.
const tokenRules = [
  {
    selector: `Literal[value=/\\b${PALETTE}\\b/]`,
    message: `Tailwind palette colour: use a token (foreground, muted-foreground, brand, destructive, success, warning, ...). A new colour is a token in app/globals.css. ${KIT}`,
  },
  {
    selector: `TemplateElement[value.raw=/\\b${PALETTE}\\b/]`,
    message: `Tailwind palette colour: use a token. ${KIT}`,
  },
  {
    selector: "Literal[value=/\\bcursor-default\\b/]",
    message: `Clickable elements show the pointer cursor (cursor-pointer); disabled ones cursor-not-allowed. ${KIT}`,
  },
];

// Pages and feature components: compose the kit, never draw controls by hand.
const featureRules = [
  ...tokenRules,
  {
    selector: "JSXOpeningElement[name.name='button']",
    message: `Raw <button>: use Button (ui/button), LinkButton or another kit component. ${KIT}`,
  },
  {
    selector: "JSXOpeningElement[name.name=/^(select|textarea|datalist)$/]",
    message: `Native form control: use OptionSelect, SearchableSelect, Textarea or SuggestInput. ${KIT}`,
  },
  {
    selector: "JSXOpeningElement[name.name='input']",
    message: `Raw <input>: use Input, Checkbox, SwitchField, SearchInput or FileDrop (files). ${KIT}`,
  },
  {
    selector: "JSXOpeningElement[name.name='Input'] > JSXAttribute[name.name='type'][value.value='file']",
    message: `File field: use FileDrop (common/file-drop), the browser draws <input type="file"> in its own style. ${KIT}`,
  },
  {
    selector: "JSXOpeningElement[name.name=/^(div|span|li|p|td|tr|img|section|label)$/] > JSXAttribute[name.name='onClick']",
    message: `onClick on a non-interactive element: no pointer, no keyboard, no focus ring. Use Button (variant ghost or link) or a kit component. ${KIT}`,
  },
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: { "no-restricted-syntax": ["error", ...featureRules] },
  },
  {
    // The kit itself is built from raw elements; only the token rules apply there.
    files: ["src/components/ui/**", "src/components/common/**"],
    rules: { "no-restricted-syntax": ["error", ...tokenRules] },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
