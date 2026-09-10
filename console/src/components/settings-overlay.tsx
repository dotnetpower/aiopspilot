import type { ComponentChildren } from "preact";
import { useEffect, useRef } from "preact/hooks";
import { t } from "../i18n";
import { panelsInGroup } from "../panels";
import { panelPath } from "../router";

interface SettingsOverlayProps {
  readonly activePanelId: string;
  readonly onClose: () => void;
  readonly children: ComponentChildren;
}

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function SettingsOverlay({
  activePanelId,
  onClose,
  children,
}: SettingsOverlayProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const returnFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const bodyWasLocked = document.body.classList.contains("scroll-locked");
    document.body.classList.add("scroll-locked");
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = [...(dialogRef.current?.querySelectorAll<HTMLElement>(
        FOCUSABLE_SELECTOR,
      ) ?? [])].filter((element) => !element.hasAttribute("disabled"));
      if (focusable.length === 0) {
        event.preventDefault();
        closeRef.current?.focus();
        return;
      }
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => {
      window.removeEventListener("keydown", onKeyDown, true);
      if (!bodyWasLocked) document.body.classList.remove("scroll-locked");
      returnFocus?.focus();
    };
  }, []);

  return (
    <div
      class="settings-overlay-scrim"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        id="settings-overlay"
        class="settings-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-overlay-title"
      >
        <header class="settings-overlay-header">
          <div>
            <h2 id="settings-overlay-title">{t("nav.group.settings")}</h2>
            <p>{t("nav.groupHint.settings")}</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            class="settings-overlay-close"
            aria-label={t("settings.close")}
            onClick={onClose}
          >
            <svg
              aria-hidden="true"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            >
              <path d="M6 6 18 18M18 6 6 18" />
            </svg>
          </button>
        </header>
        <div class="settings-overlay-workspace">
          <nav class="settings-overlay-navigation" aria-label={t("settings.menuLabel")}>
            <ul>
              {panelsInGroup("settings").map((panel) => (
                <li key={panel.id}>
                  <a
                    href={panelPath(panel.id)}
                    class={panel.id === activePanelId ? "active" : ""}
                    aria-current={panel.id === activePanelId ? "page" : undefined}
                  >
                    <strong>{panel.label}</strong>
                    {panel.subtitle ? <small>{panel.subtitle}</small> : null}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          <div class="settings-overlay-content">{children}</div>
        </div>
      </section>
    </div>
  );
}
