SUBJECT: Your AWS Bedrock API key and migration guide — [APP NAME]

---

Hi team,

We are migrating [APP NAME] from the direct Anthropic API to AWS Bedrock.

Attached is USER-GUIDE-bedrock-migration.pdf with full instructions (SDK changes, model IDs, code examples, and troubleshooting). This email contains your credentials only.

YOUR BEDROCK CREDENTIALS

  Environment variable:  AWS_BEARER_TOKEN_BEDROCK
  Bedrock API key:       [PASTE KEY HERE]
  AWS region:            us-east-1
  IAM user:              [e.g. app-my-service-bedrock]

For local testing, set these before running your app:

  export AWS_REGION=us-east-1
  export AWS_BEARER_TOKEN_BEDROCK=[PASTE KEY HERE]

Use AWS_BEARER_TOKEN_BEDROCK exactly — not AWS_BEARER_TOKEN.

For staging and production, store the key in your app's secret store and inject it at runtime. Do not commit the key to git.

SECURITY

  - This key is for Bedrock access only, scoped to [APP NAME]. Do not share outside the app team.
  - Do not forward this email or paste the key into Slack, Teams, Jira, or Confluence.
  - After copying the key into your secret store, delete this email from your inbox.
  - If the key is exposed, contact [PLATFORM TEAM EMAIL] immediately.
  - Remove ANTHROPIC_API_KEY from all environments once Bedrock is working.

NEXT STEPS

  1. Save the key to your secret store.
  2. Follow the attached user guide to update your application.
  3. Test in non-production, then deploy and remove ANTHROPIC_API_KEY.

Questions: [PLATFORM TEAM EMAIL]

Thanks,
[YOUR NAME]
[YOUR TEAM]

ATTACHMENT: USER-GUIDE-bedrock-migration.pdf
