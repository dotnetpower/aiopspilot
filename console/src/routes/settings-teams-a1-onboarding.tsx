import { ExternalLink } from "../components/ui";
import { settingsIntegrationsText } from "./settings-integrations.i18n";

const AZURE_PORTAL_URL = "https://portal.azure.com/";
const TEAMS_ADMIN_URL = "https://admin.teams.microsoft.com/policies/manage-apps";

/**
 * Explains the split between protected FDAI automation and provider-hosted
 * human approval without collecting credentials in the Console.
 */
export function TeamsA1OnboardingGuide() {
  return (
    <section
      class="settings-teams-a1-onboarding"
      aria-labelledby="settings-teams-a1-onboarding-title"
    >
      <div>
        <h5 id="settings-teams-a1-onboarding-title">
          {settingsIntegrationsText("a1OnboardingTitle")}
        </h5>
        <p>{settingsIntegrationsText("a1OnboardingDescription")}</p>
      </div>
      <div class="settings-teams-a1-onboarding-columns">
        <div>
          <strong>{settingsIntegrationsText("a1AutomatedTitle")}</strong>
          <ul>
            <li>{settingsIntegrationsText("a1AutomatedBot")}</li>
            <li>{settingsIntegrationsText("a1AutomatedSso")}</li>
            <li>{settingsIntegrationsText("a1AutomatedDeployment")}</li>
          </ul>
        </div>
        <div>
          <strong>{settingsIntegrationsText("a1HumanTitle")}</strong>
          <ol>
            <li>{settingsIntegrationsText("a1HumanOauth")}</li>
            <li>{settingsIntegrationsText("a1HumanInstall")}</li>
            <li>{settingsIntegrationsText("a1HumanApproval")}</li>
          </ol>
        </div>
      </div>
      <p class="settings-teams-a1-onboarding-note">
        {settingsIntegrationsText("a1SecretBoundary")}
      </p>
      <div class="settings-teams-a1-onboarding-actions">
        <ExternalLink href={AZURE_PORTAL_URL}>
          {settingsIntegrationsText("a1OpenAzure")}
        </ExternalLink>
        <ExternalLink href={TEAMS_ADMIN_URL}>
          {settingsIntegrationsText("a1OpenTeamsAdmin")}
        </ExternalLink>
      </div>
    </section>
  );
}
