import { resetPlaywrightDatabase } from "./support/db.ts";

async function globalSetup() {
  resetPlaywrightDatabase();
}

export default globalSetup;
