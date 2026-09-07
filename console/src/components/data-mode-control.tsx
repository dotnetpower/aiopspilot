import type { ConsoleDataMode } from "../console-data-mode";
import { t } from "../i18n";

export function DataModeControl({
  mode,
  onChange,
}: {
  readonly mode: ConsoleDataMode;
  readonly onChange: (mode: ConsoleDataMode) => void;
}) {
  return (
    <div class="data-mode-control" role="group" aria-label={t("dataMode.label")}>
      <button
        type="button"
        class={mode === "sample" ? "is-active" : ""}
        aria-pressed={mode === "sample"}
        onClick={() => onChange("sample")}
      >
        {t("dataMode.sample")}
      </button>
      <button
        type="button"
        class={mode === "live" ? "is-active" : ""}
        aria-pressed={mode === "live"}
        onClick={() => onChange("live")}
      >
        {t("dataMode.live")}
      </button>
    </div>
  );
}
