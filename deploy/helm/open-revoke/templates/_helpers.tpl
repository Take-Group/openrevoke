{{/* Names, labels and the values several templates share. */}}

{{- define "open-revoke.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "open-revoke.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Name of one component's resources: <fullname>-<component>. */}}
{{- define "open-revoke.component" -}}
{{- printf "%s-%s" (include "open-revoke.fullname" .root) .component | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "open-revoke.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "open-revoke.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: open-revoke
{{- end }}

{{/* Selector labels of one component; call with (dict "root" $ "component" "app"). */}}
{{- define "open-revoke.selectorLabels" -}}
app.kubernetes.io/name: {{ include "open-revoke.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "open-revoke.componentLabels" -}}
{{ include "open-revoke.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/* image: repository:tag, the tag defaulting to the chart's appVersion. */}}
{{- define "open-revoke.image" -}}
{{- printf "%s:%s" .image.repository (toString (default .root.Chart.AppVersion .image.tag)) }}
{{- end }}

{{- define "open-revoke.secretName" -}}
{{- default (include "open-revoke.fullname" .) .Values.secrets.existingSecret }}
{{- end }}

{{- define "open-revoke.publicUrl" -}}
{{- if .Values.publicUrl }}
{{- .Values.publicUrl | trimSuffix "/" }}
{{- else if and .Values.ingress.enabled .Values.ingress.host }}
{{- printf "%s://%s" (ternary "https" "http" .Values.ingress.tls.enabled) .Values.ingress.host }}
{{- else }}
{{- print "http://localhost:18410" }}
{{- end }}
{{- end }}

{{/* PostgreSQL the app and Temporal use: the bundled one or externalDatabase. */}}
{{- define "open-revoke.db.host" -}}
{{- if .Values.postgresql.enabled }}
{{- include "open-revoke.component" (dict "root" . "component" "postgresql") }}
{{- else }}
{{- required "externalDatabase.host is required when postgresql.enabled is false" .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{- define "open-revoke.db.port" -}}
{{- if .Values.postgresql.enabled }}5432{{ else }}{{ .Values.externalDatabase.port }}{{ end }}
{{- end }}

{{- define "open-revoke.db.user" -}}
{{- if .Values.postgresql.enabled }}postgres{{ else }}{{ .Values.externalDatabase.user }}{{ end }}
{{- end }}

{{- define "open-revoke.db.name" -}}
{{- if .Values.postgresql.enabled }}open_revoke{{ else }}{{ .Values.externalDatabase.database }}{{ end }}
{{- end }}

{{- define "open-revoke.redisHost" -}}
{{- include "open-revoke.component" (dict "root" . "component" "redis") }}
{{- end }}

{{- define "open-revoke.temporalHost" -}}
{{- include "open-revoke.component" (dict "root" . "component" "temporal") }}
{{- end }}

{{/* Env of PostgreSQL's password from the Secret; Temporal and the app read it. */}}
{{- define "open-revoke.db.passwordEnv" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "open-revoke.secretName" . }}
      key: POSTGRES_PASSWORD
{{- end }}

{{/* Connection of Temporal's server and admin tools to PostgreSQL (env names of the images). */}}
{{- define "open-revoke.temporalDbEnv" -}}
- name: TZ
  value: {{ .Values.timezone | quote }}
- name: DB
  value: postgres12
- name: DB_PORT
  value: {{ include "open-revoke.db.port" . | quote }}
- name: POSTGRES_SEEDS
  value: {{ include "open-revoke.db.host" . | quote }}
- name: POSTGRES_USER
  value: {{ include "open-revoke.db.user" . | quote }}
- name: POSTGRES_PWD
  valueFrom:
    secretKeyRef:
      name: {{ include "open-revoke.secretName" . }}
      key: POSTGRES_PASSWORD
{{- end }}

{{/* Pod settings every component shares: no Kubernetes API token, no service links. Service
links would add variables such as <RELEASE>_REDIS_PORT=tcp://... to the environment. */}}
{{- define "open-revoke.podDefaults" -}}
automountServiceAccountToken: false
enableServiceLinks: false
{{- with .Values.imagePullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{/* nodeSelector, tolerations and affinity of one component's values. */}}
{{- define "open-revoke.scheduling" -}}
{{- with .nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{- /*
Restricted container security context (Pod Security Standard "restricted"): no privilege
escalation, no capabilities, the runtime's seccomp profile, and a fixed non-root user. Called with
(dict "uid" 1000 "gid" 1000): the user the image itself runs as.
*/ -}}
{{- define "open-revoke.restrictedContainer" -}}
allowPrivilegeEscalation: false
capabilities:
  drop: ["ALL"]
seccompProfile:
  type: RuntimeDefault
runAsNonRoot: true
runAsUser: {{ .uid }}
runAsGroup: {{ .gid }}
{{- end }}
