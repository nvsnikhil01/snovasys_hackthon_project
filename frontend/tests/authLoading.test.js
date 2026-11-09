import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { AuthSubmitButton } from "../src/AuthSubmitButton.js";

test("login loading button is disabled, visible, and announced to assistive technology", () => {
  const html = renderToStaticMarkup(createElement(AuthSubmitButton, { loading: true, mode: "login" }));
  assert.match(html, /disabled/);
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /class="loading-spinner"/);
  assert.match(html, /role="status"/);
  assert.match(html, /Logging in/);
});

test("registration loading button is disabled and reports account creation", () => {
  const html = renderToStaticMarkup(createElement(AuthSubmitButton, { loading: true, mode: "register" }));
  assert.match(html, /disabled/);
  assert.match(html, /Creating account/);
});

test("auth button returns to its enabled idle label after loading", () => {
  const login = renderToStaticMarkup(createElement(AuthSubmitButton, { loading: false, mode: "login" }));
  const register = renderToStaticMarkup(createElement(AuthSubmitButton, { loading: false, mode: "register" }));
  assert.doesNotMatch(login, /disabled|loading-spinner|aria-busy="true"/);
  assert.match(login, /Log in/);
  assert.match(register, /Create account/);
});
