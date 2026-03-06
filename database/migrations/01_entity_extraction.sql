alter table reels 
add column if not exists intent_category text,
add column if not exists intent_description text,
add column if not exists intent_keywords jsonb;

create table if not exists reel_entities (
  id uuid default gen_random_uuid() primary key,
  reel_id uuid references reels(id) on delete cascade,
  entity_id text,
  name text not null,
  brand text,
  type text,
  sub_category text,
  search_query text,
  confidence float,
  source text default 'intent_extraction',
  notes text,
  created_at timestamptz default now()
);

create index if not exists idx_reel_entities_reel_id on reel_entities(reel_id);
