-- ============================================================================
-- 20260818_034_gamification_cosmetics.sql
-- Gamification Phase 2 — Cosmetics (PRD-gamification.md §7, §11, §14 Phase 2)
--
-- The cosmetics layer on top of the Phase 1 economy: an org-scoped item catalog,
-- per-student inventory + loadout, and an atomic coin-spend RPC that debits the
-- append-only coin_ledger and grants the item in one transaction (§7.1).
--
-- Subject key: CE student_id (TEXT), matching Phase 1 tables.
--
-- Security model (matches 20260817_033_gamification_core.sql): RLS enabled
-- everywhere; authenticated org members may SELECT their org's rows via
-- is_org_member(); all writes are service-role only (Next.js / Flask, BYPASSRLS).
-- The spend_coins RPC is SECURITY DEFINER and only ever called service-role.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / ON CONFLICT DO NOTHING). Reuses the
-- gamification_touch_updated_at() trigger defined in migration 033.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- items — org-scoped cosmetic catalog (§7.2). Purchasable/trophy/default.
-- price_coins NULL ⇒ not buyable (trophies + free defaults). All cosmetic.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  sku               TEXT NOT NULL,
  slot              TEXT NOT NULL,                 -- shield | armor | cloak | helmet | weapon | pet | background | frame | effect
  rarity            TEXT NOT NULL DEFAULT 'common' CHECK (rarity IN ('common','rare','epic','legendary')),
  kind              TEXT NOT NULL DEFAULT 'purchasable' CHECK (kind IN ('purchasable','trophy','default')),
  price_coins       INT,                           -- NULL for trophy/default; whole numbers (§7.1)
  name_ru           TEXT NOT NULL,
  name_kk           TEXT NOT NULL,
  name_en           TEXT NOT NULL,
  description_ru    TEXT,
  description_kk    TEXT,
  description_en    TEXT,
  art_url           TEXT,
  anim_url          TEXT,
  is_placeholder_art BOOLEAN NOT NULL DEFAULT true, -- track replacement progress (D-9)
  available         BOOLEAN NOT NULL DEFAULT true,
  available_from    TIMESTAMPTZ,
  available_until   TIMESTAMPTZ,
  acquisition_note  TEXT,                           -- trophy provenance, etc.
  sort_order        INT NOT NULL DEFAULT 0,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, sku)
);
CREATE INDEX IF NOT EXISTS idx_items_org_slot ON items (organization_id, slot, sort_order);

DROP TRIGGER IF EXISTS trg_items_updated ON items;
CREATE TRIGGER trg_items_updated
  BEFORE UPDATE ON items
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- player_items — per-student inventory. UNIQUE(student, item): own-once (§7.3).
-- Trophies are permanent; no delete path is exposed to clients.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id      TEXT NOT NULL,
  item_id         UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  acquired_via    TEXT NOT NULL DEFAULT 'purchase' CHECK (acquired_via IN ('purchase','default','trophy','admin_grant')),
  season_id       UUID,                            -- set for trophies (Phase 3)
  acquired_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, student_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_player_items_student ON player_items (organization_id, student_id);

-- ---------------------------------------------------------------------------
-- player_loadout — one equipped item per slot. Avatar composites slot layers.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_loadout (
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id      TEXT NOT NULL,
  slot            TEXT NOT NULL,
  item_id         UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, student_id, slot)
);

-- ============================================================================
-- spend_coins — atomic purchase: balance check + coin debit + inventory grant.
-- Balance is authoritative as SUM(coin_ledger) (§5.2); the ledger row uses a
-- deterministic idempotency_key so a double-submit can never double-charge, and
-- UNIQUE(student,item) makes re-buying an owned item a no-op. Returns a JSON
-- status the API layer maps to HTTP.
-- ============================================================================
CREATE OR REPLACE FUNCTION spend_coins(p_org UUID, p_student TEXT, p_item UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_item     items%ROWTYPE;
  v_balance  NUMERIC(10,1);
  v_price    INT;
  v_key      TEXT;
BEGIN
  -- Serialize concurrent purchases for this (org, student).
  PERFORM pg_advisory_xact_lock(hashtext(p_org::text || ':' || p_student));

  SELECT * INTO v_item FROM items WHERE id = p_item AND organization_id = p_org;
  IF NOT FOUND THEN
    RETURN jsonb_build_object('status', 'not_found');
  END IF;

  IF v_item.kind <> 'purchasable' OR v_item.price_coins IS NULL THEN
    RETURN jsonb_build_object('status', 'not_purchasable');
  END IF;

  IF v_item.available = false
     OR (v_item.available_from IS NOT NULL AND now() < v_item.available_from)
     OR (v_item.available_until IS NOT NULL AND now() > v_item.available_until) THEN
    RETURN jsonb_build_object('status', 'unavailable');
  END IF;

  SELECT COALESCE(SUM(amount), 0) INTO v_balance
    FROM coin_ledger WHERE organization_id = p_org AND student_id = p_student;

  -- Idempotent: already owned ⇒ no charge, report current balance.
  IF EXISTS (SELECT 1 FROM player_items
             WHERE organization_id = p_org AND student_id = p_student AND item_id = p_item) THEN
    RETURN jsonb_build_object('status', 'already_owned', 'balance', v_balance);
  END IF;

  v_price := v_item.price_coins;
  IF v_balance < v_price THEN
    RETURN jsonb_build_object('status', 'insufficient_balance', 'balance', v_balance, 'price', v_price);
  END IF;

  v_key := 'spend:' || p_org::text || ':' || p_student || ':' || p_item::text;

  INSERT INTO coin_ledger (organization_id, student_id, amount, source, source_id, idempotency_key)
    VALUES (p_org, p_student, -v_price, 'spend', p_item::text, v_key)
    ON CONFLICT (idempotency_key) DO NOTHING;

  INSERT INTO player_items (organization_id, student_id, item_id, acquired_via)
    VALUES (p_org, p_student, p_item, 'purchase')
    ON CONFLICT (organization_id, student_id, item_id) DO NOTHING;

  -- Refresh the materialized balance cache (authoritative value is the ledger).
  UPDATE player_gamification
    SET coin_balance = v_balance - v_price, updated_at = now()
    WHERE organization_id = p_org AND student_id = p_student;

  RETURN jsonb_build_object('status', 'ok', 'balance', v_balance - v_price, 'item_id', p_item);
END;
$$;

REVOKE ALL ON FUNCTION spend_coins(UUID, TEXT, UUID) FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- Row Level Security — read own-org (authenticated); writes service-role only.
-- ============================================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['items', 'player_items', 'player_loadout'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    EXECUTE format('REVOKE ALL ON %I FROM anon, authenticated;', t);
    EXECUTE format('GRANT SELECT ON %I TO authenticated;', t);
    EXECUTE format('DROP POLICY IF EXISTS "org_member_read" ON %I;', t);
    EXECUTE format(
      'CREATE POLICY "org_member_read" ON %I FOR SELECT USING (is_org_member(%I.organization_id));',
      t, t
    );
  END LOOP;
END $$;

-- ============================================================================
-- Seed the placeholder catalog for the Chess Empire org (D-9).
-- Rows generated by frontend/scripts/gen-placeholder-items.mjs (same SVGs that
-- ship under public/gamification/items/). ON CONFLICT keeps re-runs safe.
-- ============================================================================
INSERT INTO items (organization_id, sku, slot, rarity, kind, price_coins, name_en, name_ru, name_kk, art_url, sort_order)
SELECT o.id, c.sku, c.slot, c.rarity, c.kind, c.price_coins, c.name_en, c.name_ru, c.name_kk, c.art_url, c.sort_order
FROM organizations o
CROSS JOIN (VALUES
  ('shield_bronze','shield','common','default',NULL,'Bronze Shield','Бронзовый щит','Қола қалқан','/gamification/items/shield_bronze.svg',1),
  ('shield_iron','shield','common','purchasable',10,'Iron Shield','Железный щит','Темір қалқан','/gamification/items/shield_iron.svg',2),
  ('shield_azure','shield','rare','purchasable',30,'Azure Shield','Лазурный щит','Көгілдір қалқан','/gamification/items/shield_azure.svg',3),
  ('shield_dragon','shield','epic','purchasable',75,'Dragon Shield','Драконий щит','Айдаһар қалқаны','/gamification/items/shield_dragon.svg',4),
  ('helmet_leather','helmet','common','default',NULL,'Leather Cap','Кожаный шлем','Былғары дулыға','/gamification/items/helmet_leather.svg',5),
  ('helmet_knight','helmet','rare','purchasable',30,'Knight Helm','Рыцарский шлем','Рыцарь дулығасы','/gamification/items/helmet_knight.svg',6),
  ('helmet_royal','helmet','epic','purchasable',75,'Royal Helm','Королевский шлем','Патша дулығасы','/gamification/items/helmet_royal.svg',7),
  ('weapon_dagger','weapon','common','purchasable',10,'Dagger','Кинжал','Қанжар','/gamification/items/weapon_dagger.svg',8),
  ('weapon_sword','weapon','rare','purchasable',30,'Steel Sword','Стальной меч','Болат қылыш','/gamification/items/weapon_sword.svg',9),
  ('weapon_flameblade','weapon','legendary','purchasable',150,'Flameblade','Пламенный клинок','Жалынды семсер','/gamification/items/weapon_flameblade.svg',10),
  ('armor_tunic','armor','common','default',NULL,'Cloth Tunic','Холщовая туника','Мата көйлек','/gamification/items/armor_tunic.svg',11),
  ('armor_chain','armor','rare','purchasable',30,'Chainmail','Кольчуга','Сауыт','/gamification/items/armor_chain.svg',12),
  ('armor_plate','armor','epic','purchasable',75,'Plate Armor','Латные доспехи','Тақта сауыт','/gamification/items/armor_plate.svg',13),
  ('cloak_gray','cloak','common','purchasable',10,'Gray Cloak','Серый плащ','Сұр шапан','/gamification/items/cloak_gray.svg',14),
  ('cloak_royal','cloak','rare','purchasable',30,'Royal Cloak','Королевский плащ','Патша шапаны','/gamification/items/cloak_royal.svg',15),
  ('pet_kitten','pet','common','purchasable',10,'Kitten','Котёнок','Мысық','/gamification/items/pet_kitten.svg',16),
  ('pet_falcon','pet','rare','purchasable',30,'Falcon','Сокол','Сұңқар','/gamification/items/pet_falcon.svg',17),
  ('pet_dragon','pet','legendary','purchasable',150,'Baby Dragon','Дракончик','Кішкентай айдаһар','/gamification/items/pet_dragon.svg',18),
  ('background_meadow','background','common','default',NULL,'Meadow','Луг','Шалғын','/gamification/items/background_meadow.svg',19),
  ('background_castle','background','rare','purchasable',30,'Castle','Замок','Қамал','/gamification/items/background_castle.svg',20),
  ('background_nebula','background','epic','purchasable',75,'Nebula','Туманность','Тұмандық','/gamification/items/background_nebula.svg',21),
  ('frame_bronze','frame','common','purchasable',10,'Bronze Frame','Бронзовая рамка','Қола жақтау','/gamification/items/frame_bronze.svg',22),
  ('frame_gold','frame','legendary','purchasable',150,'Gold Frame','Золотая рамка','Алтын жақтау','/gamification/items/frame_gold.svg',23),
  ('effect_sparkle','effect','rare','purchasable',30,'Sparkle','Искры','Ұшқын','/gamification/items/effect_sparkle.svg',24),
  ('effect_aura','effect','epic','purchasable',75,'Aura','Аура','Аура','/gamification/items/effect_aura.svg',25)
) AS c(sku, slot, rarity, kind, price_coins, name_en, name_ru, name_kk, art_url, sort_order)
WHERE o.slug = 'chess-empire'
ON CONFLICT (organization_id, sku) DO NOTHING;

-- ============================================================================
-- ROLLBACK (manual):
--   DROP FUNCTION IF EXISTS spend_coins(UUID, TEXT, UUID);
--   DROP TABLE IF EXISTS player_loadout, player_items, items CASCADE;
-- ============================================================================
