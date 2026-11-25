// Minimal reader of the JSON Schema a connector publishes as `config_schema`
// (Pydantic `model_json_schema()`). Supports what a connection form needs:
// string, number, integer, boolean, enum and string arrays, optional fields
// written as `anyOf: [X, {type: null}]`, and `$ref` into `$defs`.

type JsonObject = Record<string, unknown>;

export type FieldType = "string" | "number" | "integer" | "boolean" | "enum" | "string_list";

export interface SchemaField {
  name: string;
  title: string;
  description: string | null;
  type: FieldType;
  required: boolean;
  /** For enums. */
  options: string[];
  /** "uri", "email", "password", ... */
  format: string | null;
  defaultValue: unknown;
  placeholder: string | null;
  /** Rendered as a password input; the value goes to `secrets`, not `config`. */
  secret: boolean;
  /** Multi-line text (e.g. a service account JSON). */
  multiline: boolean;
  /** Regex for the browser's own validation. */
  pattern: string | null;
}

/** Form state: text for everything except booleans. */
export type FieldValue = string | boolean;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function resolveRef(schema: JsonObject, root: JsonObject): JsonObject {
  const ref = schema.$ref;
  if (typeof ref !== "string" || !ref.startsWith("#/")) return schema;
  let node: unknown = root;
  for (const part of ref.slice(2).split("/")) node = isObject(node) ? node[part] : undefined;
  return isObject(node) ? { ...node, ...schema, $ref: undefined } : schema;
}

/** `anyOf: [{type: string}, {type: null}]` -> `{type: string}`. */
function unwrapOptional(schema: JsonObject, root: JsonObject): JsonObject {
  const variants = schema.anyOf ?? schema.oneOf;
  if (Array.isArray(variants)) {
    const concrete = variants.filter((v) => isObject(v) && v.type !== "null") as JsonObject[];
    if (concrete.length === 1) return { ...schema, ...resolveRef(concrete[0], root), anyOf: undefined, oneOf: undefined };
  }
  return resolveRef(schema, root);
}

function fieldType(schema: JsonObject): FieldType {
  if (Array.isArray(schema.enum)) return "enum";
  switch (schema.type) {
    case "boolean":
      return "boolean";
    case "integer":
      return "integer";
    case "number":
      return "number";
    case "array":
      return "string_list";
    default:
      return "string";
  }
}

function humanizeName(name: string): string {
  const text = name.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Fields of the form: config properties first, then secrets the schema does not describe. */
export function schemaFields(schema: JsonObject, secretFields: string[]): SchemaField[] {
  const properties = isObject(schema.properties) ? schema.properties : {};
  const required = new Set(Array.isArray(schema.required) ? (schema.required as string[]) : []);
  const secrets = new Set(secretFields);

  const fields: SchemaField[] = Object.entries(properties).map(([name, raw]) => {
    const prop = unwrapOptional(isObject(raw) ? raw : {}, schema);
    const format = typeof prop.format === "string" ? prop.format : null;
    const examples = Array.isArray(prop.examples) ? prop.examples : [];
    // The backend marks secrets with `secret: true` (and lists them in secret_fields).
    const secret = secrets.has(name) || prop.secret === true || format === "password" || prop.writeOnly === true;
    return {
      name,
      title: typeof prop.title === "string" ? prop.title : humanizeName(name),
      description: typeof prop.description === "string" ? prop.description : null,
      type: fieldType(prop),
      required: required.has(name),
      options: Array.isArray(prop.enum) ? prop.enum.map(String) : [],
      format,
      defaultValue: prop.default,
      placeholder: examples.length > 0 ? String(examples[0]) : null,
      secret,
      multiline: prop["x-multiline"] === true || format === "textarea" || format === "json" || /json/i.test(name),
      pattern: typeof prop.pattern === "string" ? prop.pattern : null,
    };
  });

  for (const name of secretFields) {
    if (name in properties) continue;
    fields.push({
      name,
      title: humanizeName(name),
      description: null,
      type: "string",
      required: false,
      options: [],
      format: null,
      defaultValue: undefined,
      placeholder: null,
      secret: true,
      multiline: /json/i.test(name),
      pattern: null,
    });
  }
  return fields;
}

/** Form state from the saved config (secrets always start empty). */
export function initialValues(fields: SchemaField[], config: Record<string, unknown>): Record<string, FieldValue> {
  const values: Record<string, FieldValue> = {};
  for (const field of fields) {
    if (field.secret) {
      values[field.name] = "";
      continue;
    }
    const current = field.name in config ? config[field.name] : field.defaultValue;
    if (field.type === "boolean") values[field.name] = current === true;
    else if (field.type === "string_list") values[field.name] = Array.isArray(current) ? current.join("\n") : "";
    else values[field.name] = current === undefined || current === null ? "" : String(current);
  }
  return values;
}

/** Splits form state into `config` (typed) and `secrets` (only fields the user filled in). */
export function buildPayload(
  fields: SchemaField[],
  values: Record<string, FieldValue>,
): { config: Record<string, unknown>; secrets: Record<string, string> } {
  const config: Record<string, unknown> = {};
  const secrets: Record<string, string> = {};
  for (const field of fields) {
    const value = values[field.name];
    if (field.secret) {
      if (typeof value === "string" && value.trim() !== "") secrets[field.name] = value;
      continue;
    }
    if (field.type === "boolean") {
      config[field.name] = value === true;
      continue;
    }
    const text = typeof value === "string" ? value.trim() : "";
    if (text === "") {
      if (field.required) config[field.name] = text;
      continue;
    }
    if (field.type === "integer" || field.type === "number") config[field.name] = Number(text);
    else if (field.type === "string_list") config[field.name] = text.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean);
    else config[field.name] = text;
  }
  return { config, secrets };
}
