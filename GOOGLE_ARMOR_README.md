### Google Model Armor interceptor
A step‑by‑step guide to spinning up **Google Cloud Model Armor** — complete with Compute Engine dependencies, **KMS encryption**, and four ready‑to‑use templates (**basic filter · inspect · de‑identify · re‑identify**) — using nothing but the **gcloud CLI**.

1. **Prerequisites**
2. **Environment Variables**
3. **Authenticate** with a service‑account key.
4. **Create** a new project & attach it to a **Billing Account**.
5. **Enable** the Model Armor, Compute, and KMS APIs.
6. **Create** four templates (basic filter, inspect, de‑id, re‑id).
7. **Provision** a Cloud KMS key ring + key, generate an AES‑256 DEK, and **wrap** it.
8. **Export** the wrapped key to `.env` (or Secret Manager).



#### 1.  Prerequisites
Model Armor relies on Google Cloud APIs that require billing and authentication. The service account is necessary to automate deployment and API calls.

| Tool / Resource                  | Version / Role | Notes |
|---------------------------------|----------------|-------|
| **gcloud CLI**                  | ≥ 460          | `gcloud version` |
| **openssl**                     | any            | Generate AES key |
| **Service‑account JSON key**    | Project Owner  | Activate via `gcloud auth` |
| **Billing Account**             | Billing Admin  | Needed for new project |



#### 2. Environment Variables
Add following variables to main [environment variables](#environment-variables)
|Variable|Default|Description|
|---|---|---|
|GOOGLE_PROJECT|llm-prompts-guard|GCP project name|
|GOOGLE_REGION|us-central1|GCP region|
|GOOGLE_INSPECT_TEMPLATE|pii-advance|inspect template|
|GOOGLE_DEIDENTIFY_TEMPLATE|pii-deidentify|PII deidentify template name|
|GOOGLE_KMS_KEY_NAME|-|PATH to DLP key|
|GOOGLE_KMS_WRAPPED_KEY|-|KMS wrapped key base64|
|GOOGLE_SURROGATE_INFO_TYPE|PII_TOKEN|Surrogate token name in re-identify template|
|GOOGLE_APPLICATION_CREDENTIALS|-|Local path to credentials file|



#### 3.  Authenticate
Activate the service account and set it as the active one
```bash
gcloud auth activate-service-account        --key-file ./secret/xxx‑key.json

gcloud config set account "$(jq -r .client_email < ./secret/xxx‑key.json)"
```

#### 4.  Create & Fund the Project
A project is the security + billing boundary for Model Armor.
Without billing, the Model Armor API refuses to enable.

```bash
# Create the project
gcloud projects create "$PROJECT_ID"        --name "Model Armor Demo"

# Link to a billing account
gcloud billing projects link "$PROJECT_ID"        --billing-account "$BILLING_ACCOUNT_ID"
```

#### 5.  Enable Required APIs

```bash
# Point gcloud at the regional Model Armor endpoint
gcloud config set api_endpoint_overrides/modelarmor        "https://modelarmor.$LOCATION_ID.rep.googleapis.com/"

# Enable the services
gcloud services enable compute.googleapis.com   --project "$PROJECT_ID"
gcloud services enable modelarmor.googleapis.com --project "$PROJECT_ID"
gcloud services enable cloudkms.googleapis.com   --project "$PROJECT_ID"
```

#### 6.  Create Model Armor Templates
Model Armor controls are template‑driven – each template is an immutable set of rules that the interceptor references by name.

#### 6.1  Basic Filter Template

```bash
gcloud model-armor templates create "$BASIC_TEMPLATE_ID"        --location "$REGION"        --basic-config-filter-enforcement=enabled
```

#### 6.2  Inspect Template (custom infoTypes)
Adds structured findings so downstream logic can decide to redact, log, or allow.

```bash
cat > inspect-config.json <<'EOF'
{
  "inspectConfig": {
    "infoTypes": [
      { "name": "EMAIL_ADDRESS" },
      { "name": "PHONE_NUMBER" },
      { "name": "CREDIT_CARD_NUMBER" }
    ],
    "includeQuote": true
  }
}
EOF

gcloud model-armor templates create "$INSPECT_TEMPLATE_ID"        --location "$REGION"        --inspect-config=@inspect-config.json
```

#### 6.3  De‑identify Template (strip findings)
De-identification templates specify the rules and methods for transforming sensitive data (e.g., PII, financial details) to protect privacy while still allowing for data analysis or model training.
```bash
cat > deidentify-config.json <<'EOF'
{
  "transformationConfigs": [
    {
      "primitiveTransform": {
        "removeFindings": true
      }
    }
  ]
}
EOF

gcloud model-armor templates create "$DEID_TEMPLATE_ID"        --location "$REGION"        --deidentify-config=@deidentify-config.json
```

#### 6.4  Re‑identify Template (surrogate tokens)
Turns PII_TOKEN placeholders back into real data after the LLM responds.

```bash
cat > reidentify-config.json <<'EOF'
{
  "reidentifyConfig": {
    "surrogateInfoType": {
      "name": "PII‑TOKEN"
    }
  }
}
EOF

gcloud model-armor templates create "$REID_TEMPLATE_ID"        --location "$REGION"        --reidentify-config=@reidentify-config.json
```

#### 6.5  Verify

```bash
gcloud model-armor templates list --location "$LOCATION_ID"
# Should list: basic‑guard, inspect‑guard, deid‑guard, reid‑guard
```

---

#### 7.  Provision Cloud KMS

```bash
# Key ring
gcloud kms keyrings create "dlp-keyring" --location global --project "$PROJECT_ID"

# Key
gcloud kms keys create "dlp-key"        --location global        --keyring dlp-keyring        --purpose encryption        --project "$PROJECT_ID"
```

---

#### 8.  Generate & Wrap a Data‑Encryption Key (DEK)

```bash
# Generate 256‑bit AES key
openssl rand -out ./aes_key.bin 32

# Base‑64 encode
PLAINTEXT_KEY=$(base64 -i ./aes_key.bin)

# Wrap using Cloud KMS
gcloud kms encrypt        --location global        --keyring dlp-keyring        --key dlp-key        --plaintext-file <(echo "$PLAINTEXT_KEY")        --ciphertext-file wrapped_key.b64        --project "$PROJECT_ID"

export WRAPPED_KEY=$(cat wrapped_key.b64)

# Persist to env
printf "\nWRAPPED_KEY=%s\n" "$WRAPPED_KEY" >> .env
```

---

#### 9.  Validate

```bash
# List templates
gcloud model-armor templates list --location "$REGION"

# Dry‑run an inspect call
gcloud model-armor templates inspect-user-prompt        --location "$REGION"        --template "$INSPECT_TEMPLATE_ID"        --user-prompt-data-text "Hi, my SSN is 123‑45‑6789"
```
