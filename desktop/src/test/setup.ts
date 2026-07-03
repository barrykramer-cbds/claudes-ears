import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// The app hydrates from GET /library on mount; default every suite to an empty
// index so component tests never hit the network. Override per test as needed.
export const emptyLibraryPage = { items: [], total: 0, page: 1, limit: 200 };

// jsdom doesn't implement the <dialog> top-layer API.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
}

vi.stubGlobal(
  "fetch",
  vi.fn((input: RequestInfo | URL) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.includes("/library")) {
      return Promise.resolve(new Response(JSON.stringify(emptyLibraryPage), { status: 200 }));
    }
    return Promise.reject(new Error(`unexpected fetch in test: ${url}`));
  }),
);
