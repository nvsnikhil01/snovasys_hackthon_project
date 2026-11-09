import { createElement } from "react";

export function AuthSubmitButton({ loading, mode }) {
  const label = loading
    ? mode === "login" ? "Logging in…" : "Creating account…"
    : mode === "login" ? "Log in" : "Create account";

  return createElement(
    "button",
    { className: "button button-primary button-wide", type: "submit", disabled: loading, "aria-busy": loading },
    loading && createElement("span", { className: "loading-spinner", "aria-hidden": "true" }),
    createElement("span", null, label),
    !loading && createElement("span", { "aria-hidden": "true" }, "→"),
    loading && createElement("span", { className: "sr-only", role: "status" }, label),
  );
}
