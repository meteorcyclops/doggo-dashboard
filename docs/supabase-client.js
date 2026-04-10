import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const cfg = window.DOGGO_GUESTBOOK_CONFIG || {};

export const guestbookCfg = cfg;
export const profileId = cfg.profileId || 'default';
export const supabase = cfg.supabaseUrl && cfg.supabaseAnonKey
  ? createClient(cfg.supabaseUrl, cfg.supabaseAnonKey)
  : null;
