import { setupServer } from "msw/node";

/**
 * Shared MSW Node server instance.
 *
 * Handlers are added per-test-file via server.use(...) or passed at
 * server.listen() time in the vitest setup.
 *
 * No default handlers are registered here — each test file provides its own
 * handlers for the specific endpoints under test.
 */
export const server = setupServer();
