import 'server-only';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';

let client: SupabaseClient | null = null;

/** Create the service-role client on first use so importing this module is side-effect free. */
function getClient(): SupabaseClient {
  if (!client) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    client = createClient(supabaseUrl, supabaseServiceKey);
  }
  return client;
}

/**
 * Lazily-initialized service-role client. `createClient` runs only on first
 * property access, so merely importing this module (e.g. via a page under test)
 * never throws "supabaseUrl is required" when SUPABASE env vars are absent.
 */
export const supabaseAdmin = new Proxy({} as SupabaseClient, {
  get(_target, prop) {
    const c = getClient();
    const value = Reflect.get(c, prop);
    // Bind methods to the real client so internal `this`/private-field access works.
    return typeof value === 'function' ? value.bind(c) : value;
  },
});
