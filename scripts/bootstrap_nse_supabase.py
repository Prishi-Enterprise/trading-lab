"""Generate an ignored SQL bootstrap from validated first-seen NSE archives.

Run once before the prospective cloud worker; never commit the output or raw bars.
"""

import json
from datetime import date
from pathlib import Path

from tradinglab.nse_only import ARCHIVES, load_series


def main():
    cutoff = date(2026, 9, 24)
    series, provenance = load_series(ARCHIVES, cutoff)
    hashes = {row["date"]: row["sha256"] for row in provenance}
    rows = []
    for symbol, bars in sorted(series.items()):
        for bar in bars:
            rows.append([str(bar.day), symbol, str(bar.open), str(bar.high), str(bar.low), str(bar.close), bar.volume, hashes[str(bar.day)]])
    rows.sort(key=lambda row: (row[0], row[1]))
    assert len(rows) == 568 and len(provenance) == 284
    payload = json.dumps(rows, separators=(",", ":"))
    sql = f"""-- Derived official NSE bars through {cutoff}; generated from locally validated archives.
-- Run only after 202609250001_nse_experiments.sql in the Trading Lab project.
with source as (select value as item from jsonb_array_elements('{payload}'::jsonb)),
bars as (
  select item->>0 as day, item->>1 as symbol, item->>2 as open_price,
         item->>3 as high_price, item->>4 as low_price, item->>5 as close_price,
         (item->>6)::bigint as volume, item->>7 as archive_sha256
  from source
)
insert into public.nse_daily_bars
  (day, symbol, open_price, high_price, low_price, close_price, volume, archive_sha256, source_url)
select day::date, symbol, open_price, high_price, low_price, close_price, volume,
       archive_sha256,
       'https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_' ||
       replace(day, '-', '') || '_F_0000.csv.zip'
from bars
on conflict (day, symbol) do nothing;
"""
    destination = Path("state/nse-only/bootstrap.sql")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(sql)
    print(f"Wrote {len(rows)} derived bars / {len(provenance)} sessions to ignored {destination} ({destination.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
