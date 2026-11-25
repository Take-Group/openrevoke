"use client";

import { useState } from "react";
import { FileJsonIcon, LogInIcon } from "lucide-react";

import { CopyField } from "@/components/common/copy-button";
import { FileDrop } from "@/components/common/file-drop";
import { FormField } from "@/components/common/form-field";
import { ExternalLinkButton } from "@/components/common/links";
import { InlineError } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { Step, Steps } from "@/components/common/steps";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStartGoogleOAuth } from "@/hooks/use-discovery";
import { errorMessage } from "@/lib/api/client";

const CONSOLE = "https://console.cloud.google.com";

/** Client ID and secret from the JSON file Google offers when the client is created. */
function parseClientFile(text: string): { clientId: string; clientSecret: string } | null {
  try {
    const data = JSON.parse(text) as { web?: { client_id?: string; client_secret?: string } };
    if (data.web?.client_id && data.web.client_secret) {
      return { clientId: data.web.client_id, clientSecret: data.web.client_secret };
    }
  } catch {
    // not JSON
  }
  return null;
}

/** Guided Connect with Google: links to each console page, then the company's own OAuth client. */
export function GoogleOAuthSetup({ redirectUri, callbackError }: { redirectUri: string; callbackError: string | null }) {
  const start = useStartGoogleOAuth();
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const error = start.error ? errorMessage(start.error) : (fileError ?? callbackError);

  async function readFile(file: File | undefined) {
    if (!file) return;
    const parsed = parseClientFile(await file.text());
    if (!parsed) {
      setFileError("This is not the JSON file of a Web application OAuth client.");
      return;
    }
    setFileError(null);
    setClientId(parsed.clientId);
    setClientSecret(parsed.clientSecret);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Panel className="lg:col-span-3" bodyClassName="p-5">
        <Steps>
          <Step n={1} title="Create a project" description="Sign in with your company account. Any name works, e.g. Open Revoke.">
            <ExternalLinkButton href={`${CONSOLE}/projectcreate`}>Create project</ExternalLinkButton>
          </Step>
          <Step
            n={2}
            title="Enable the Admin SDK API"
            description="Check that the new project is selected at the top, then click Enable."
          >
            <ExternalLinkButton href={`${CONSOLE}/apis/library/admin.googleapis.com`}>Admin SDK API</ExternalLinkButton>
          </Step>
          <Step
            n={3}
            title="Set up the consent screen"
            description={
              <>
                Click Get started: app name Open Revoke, your e-mail, audience <strong>Internal</strong>. Internal means
                only your company&apos;s accounts can use it and Google does not review it. External in Testing mode also
                works, but Google ends the access after 7 days.
              </>
            }
          >
            <ExternalLinkButton href={`${CONSOLE}/auth/overview`}>Google Auth Platform</ExternalLinkButton>
          </Step>
          <Step
            n={4}
            title="Create an OAuth client"
            description="Application type Web application. Under Authorized redirect URIs add:"
          >
            <CopyField value={redirectUri} label="redirect URI" />
            <p className="text-[0.8125rem] text-muted-foreground">
              Click Create, then Download JSON and drop the file into the form. Google shows the secret only now, so do
              it before you close the dialog.
            </p>
            <ExternalLinkButton href={`${CONSOLE}/auth/clients/create`}>Create OAuth client</ExternalLinkButton>
          </Step>
          <Step
            n={5}
            title="Sign in as a Google Workspace admin"
            description="Google asks the admin to allow: read users, suspend users (offboarding), read the audit log, and read the tokens people gave to apps. Keep all ticked; the first and the third are required. Open Revoke then imports people and runs the first scan."
          />
        </Steps>
      </Panel>
      <Panel className="self-start lg:col-span-2" bodyClassName="p-5">
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            start.mutate({ client_id: clientId.trim(), client_secret: clientSecret.trim() });
          }}
        >
          <FileDrop
            accept="application/json,.json"
            what="the client JSON file"
            icon={<FileJsonIcon />}
            onFile={(file) => void readFile(file)}
          />
          <FormField label="Client ID" htmlFor="google-client-id" required hint="Ends with .apps.googleusercontent.com">
            <Input
              id="google-client-id"
              autoComplete="off"
              spellCheck={false}
              placeholder="1234567890-abc.apps.googleusercontent.com"
              value={clientId}
              onChange={(event) => setClientId(event.target.value)}
              required
            />
          </FormField>
          <FormField label="Client secret" htmlFor="google-client-secret" required hint="Stored encrypted.">
            <Input
              id="google-client-secret"
              type="password"
              autoComplete="off"
              value={clientSecret}
              onChange={(event) => setClientSecret(event.target.value)}
              required
            />
          </FormField>
          {error && <InlineError message={error} />}
          <Button
            type="submit"
            disabled={start.isPending || start.isSuccess || !clientId || !clientSecret}
            className="self-start"
          >
            <LogInIcon />
            {start.isPending || start.isSuccess ? "Opening Google…" : "Connect with Google"}
          </Button>
        </form>
      </Panel>
    </div>
  );
}
