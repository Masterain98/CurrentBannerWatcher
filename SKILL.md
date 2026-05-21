---
name: genshin-banner-watcher
description: automates genshin impact banner announcement extraction from hoyoverse announcement content and uigf api item translation. use when chatgpt needs to fetch or process genshin game announcements, identify character, weapon, or chronicled wish banners, convert chinese character or weapon names into uigf item ids, and produce standardized banner-data json without submitting data to downstream services.
---

# Genshin Banner Watcher

## Overview

Use this skill to reproduce the non-submission workflow from CurrentBannerWatcher: fetch or ingest Genshin Impact announcement data, identify banner announcements, extract pool metadata, resolve character and weapon names to UIGF item IDs, enrich localized banner names and images, and output standardized `banner-data.json`-style data.

Do not submit, upload, publish, or POST generated banner records to any downstream endpoint. Ignore the original `POST_ENDPOINT` and `CREATION_POST_ENDPOINT` flows unless the user explicitly asks for a separate submission workflow.

## Required capabilities

Use available HTTP, browser, MCP, or connector tools to call external APIs. If no tool can make HTTP requests, ask the user to provide raw announcement JSON and, if needed, UIGF translation results.

Required external APIs:

1. HoYoVerse announcement content API
   - Method: `GET`
   - URL: `https://sg-hk4e-api-static.hoyoverse.com/common/hk4e_global/announcement/api/getAnnContent`
   - Query parameters:
     - `game=hk4e`
     - `game_biz=hk4e_global`
     - `region=os_asia`
     - `bundle_id=hk4e_global`
     - `channel_id=1`
     - `level=55`
     - `platform=pc`
     - `lang=<language>`
     - `uid=100000000`

2. UIGF translation API
   - Method: `POST`
   - URL: `https://api.uigf.org/translate/` or equivalent `/translate`
   - Body for name to ID lookup:
     ```json
     {
       "lang": "zh-cn",
       "type": "normal",
       "game": "genshin",
       "item_name": "<character_or_weapon_name>"
     }
     ```
   - Expected response includes `item_id`.
   - Batch lookup may be used by sending `item_name` as a JSON string list such as `["角色A","角色B"]`; preserve input order in the returned ID list.

Cache UIGF lookup results per run. Never silently accept missing, null, or zero item IDs.

## Core workflow

### 1. Fetch Chinese announcements

Fetch `lang=zh-cn` from the HoYoVerse announcement content API. Read `data.list` as the announcement list.

Each announcement is expected to contain at least:

- `ann_id`
- `title`
- `subtitle`
- `content`
- optional `banner`

Treat `zh-cn` as the source of truth for parsing item names, pool type, version, order, and time.

### 2. Convert HTML content to plain text

For each Chinese announcement, convert `content` HTML to text before matching. Preserve Chinese punctuation and time text. Remove incidental HTML attributes such as ` contenteditable="false"` before time matching.

Skip announcements that are not banner announcements. Do not include skipped announcements in the final output.

### 3. Normalize version labels

Use this mapping when a version appears in the newer Chinese moon-format notation:

```json
{
  "「月之一」": "6.0",
  "「月之二」": "6.1",
  "「月之三」": "6.2",
  "「月之四」": "6.3",
  "「月之五」": "6.4",
  "「月之六」": "6.5",
  "「月之七」": "6.6",
  "「月之八」": "6.7",
  "「月之九」": "6.8"
}
```

If no mapping applies, keep the original version token.

### 4. Determine banner name from subtitle

Derive the localized banner name by stripping language-specific event-wish wrappers from the announcement `subtitle`.

Apply these removals when present:

- zh-cn: `「`, `」祈愿`
- zh-tw: `「`, `」祈願`
- en-us: `Event Wish - `
- ja: `イベント祈願<br />`, `集録祈願<br />`, `」`
- ko: `「`, `」 기원`, ` 기원`
- es: `Gachapón «`, `»`
- fr: `Vœux « `, `Vœux « `, ` »`, ` `
- ru: `Молитва «`, `Молитва: `, `»`
- th: `การอธิษฐาน "`, `"`
- vi: `Cầu Nguyện "`, `Cầu Nguyện `, `"`
- de: `Gebet „`, `“`
- id: `Event Permohonan "`, `Event Permohonan `, `"`
- pt: `Oração "`, `Oração `, `"`
- tr: `" Etkinliği Dileği`, ` Etkinliği Dileği`, `"`
- it: `Desiderio `

### 5. Parse banner type and item lists

#### Character event wish

Use this branch when `title` contains `概率UP` and plain text content contains `概率提升角色`.

Pool type:

- `301` when content contains `※ 本祈愿属于「角色活动祈愿」`
- `400` when content contains `※ 本祈愿属于「角色活动祈愿-2」`

Extract character names with:

```regex
[\u4e00-\u9fa5]+(?=\(风\)|\(火\)|\(水\)|\(冰\)|\(雷\)|\(岩\)|\(草\))
```

Deduplicate while preserving first occurrence order. Resolve every name through UIGF. Require exactly 4 IDs:

- `UpOrangeList`: first ID only
- `UpPurpleList`: remaining 3 IDs

Fail with a clear diagnostic if the count is not exactly 4.

#### Weapon event wish

Use this branch when `title` contains `概率UP` and `subtitle` contains `神铸赋形`.

Set pool type to `302`.

Extract weapon names with:

```regex
·([\u4e00-\u9fa5]+)
```

Deduplicate while preserving first occurrence order. Resolve every name through UIGF. Require exactly 7 IDs:

- `UpOrangeList`: first 2 IDs
- `UpPurpleList`: remaining 5 IDs

Fail with a clear diagnostic if the count is not exactly 7.

#### Chronicled wish / collection wish

Use this branch when plain text content contains `本祈愿属于「集录祈愿」`.

Set pool type to `500`.

Remove spaces from content text, then parse sections:

```regex
5星角色：(?P<r>.*?)5星武器：
5星武器：(?P<r>.*?)4星角色：
4星角色：(?P<r>.*?)(?=4星武器：)
4星武器：(?P<r>.*?)(?=※)
```

Split each captured section on `/`. Deduplicate while preserving first occurrence order.

- `UpOrangeList`: IDs for unique 5-star characters followed by unique 5-star weapons
- `UpPurpleList`: IDs for unique 4-star characters followed by unique 4-star weapons

Do not enforce a fixed count for this branch unless the user provides an expected count.

#### Non-banner announcements

If none of the above branches match, skip the announcement.

### 6. Parse banner time, version, and order

For non-500 pool types, match banner time using this conceptual pattern:

- prefix contains `〓祈愿介绍〓祈愿时间概率提升角色（5星）概率提升角色（4星）` or the equivalent weapon form
- start is either `<version>版本更新后` or an absolute timestamp like `2025/12/03 06:00`
- end is an absolute timestamp like `2025/12/23 17:59`

For pool type `500`, use the same logic but with the prefix `〓祈愿介绍〓祈愿时间可定轨5星角色可定轨5星武器`.

If `start_time` contains `更新后`:

1. Set `order_number` to `1`.
2. Extract the version token from the start of the start text with `^(\d\.\d|「月之[一二三四五六七八九]」)`.
3. Convert moon-format versions with the version mapping.
4. Search all Chinese announcements for patch notes:
   - first try `<version>版本更新说明` or any moon-format title ending in `版本更新说明`
   - then try `<version>版本更新维护预告` or any moon-format title ending in `版本更新维护预告`
5. Extract the actual patch start timestamp from the patch note. For update notes, match `〓更新时间〓<t class="t_gl">... </t>开始` or `t_lc`. For maintenance notices, match `预计将于<t class="t_gl">... </t>进行版本更新维护` or `t_lc`.
6. Replace the relative banner start time with that actual timestamp.

If `start_time` is already absolute:

1. Set `order_number` to `2`.
2. Find the first Chinese announcement whose subtitle contains `版本更新说明`.
3. Extract version from the subtitle with `^(\d+\.\d+|「月之[一二三四五六七八九]」)`.
4. Convert moon-format versions with the version mapping.
5. Fail clearly if no version update note is found.

Always preserve the original slash-based timestamp format in primary output, such as `YYYY/MM/DD HH:mm` or `YYYY/MM/DD HH:mm:ss`.

### 7. Enrich localized banner names and images

For each accepted Chinese banner announcement, fetch these target languages:

```json
["en-us", "zh-tw", "ja", "ko", "es", "fr", "ru", "th", "vi", "de", "id", "pt", "tr", "it"]
```

For each language:

1. Fetch announcement content with `lang=<target_language>`.
2. Find the announcement with matching `ann_id`.
3. Copy the Chinese-derived generic metadata.
4. Set localized `banner_name` using the normalized target-language subtitle.
5. Set localized `banner_image` from the matched announcement's `banner` field.

Fail or report a warning if a localized announcement cannot be found. Prefer failing for production automation and warning only for exploratory runs.

### 8. Build output

Primary output must be a JSON object keyed by announcement ID. Each value must have generic metadata plus localized banner fields.

Use this exact structure:

```json
{
  "<ann_id>": {
    "UpOrangeList": [10000000],
    "UpPurpleList": [10000001, 10000002, 10000003],
    "UIGF_pool_type": 301,
    "start_time": "YYYY/MM/DD HH:mm",
    "end_time": "YYYY/MM/DD HH:mm",
    "version_number": "6.0",
    "order_number": 1,
    "zh-cn": {
      "banner_name": "...",
      "banner_image": "https://..."
    },
    "en-us": {
      "banner_name": "...",
      "banner_image": "https://..."
    }
  }
}
```

Include every available target language as a sibling key using the language code.

Do not generate or POST the original `create_banner` upload payload unless the user explicitly requests it. If the user asks for an upload-like preview, generate it as local JSON only and state that it was not submitted.

## Validation checklist

Before returning the final result, verify:

- Every included announcement has `UpOrangeList`, `UpPurpleList`, `UIGF_pool_type`, `start_time`, `end_time`, `version_number`, and `order_number`.
- Every item ID is a positive integer or a clearly valid UIGF item identifier. Do not allow `null`, `0`, missing values, or unresolved names.
- Character banners have exactly 1 orange and 3 purple IDs.
- Weapon banners have exactly 2 orange and 5 purple IDs.
- Pool type is one of `301`, `400`, `302`, or `500`.
- `order_number` is `1` for version-update-start banners and `2` for absolute-start banners.
- Each localized entry has both `banner_name` and `banner_image`.
- Non-banner announcements are skipped, not emitted as empty objects.
- No downstream submission endpoint was called.

## Error handling

When parsing fails, return a concise diagnostic containing:

- `ann_id`
- `title`
- `subtitle`
- branch attempted, such as character, weapon, chronicled, time, localization, or UIGF lookup
- the problematic raw names, regex result, or timestamp fragment
- the expected count or expected pattern

Do not guess missing item IDs. If UIGF lookup fails for a name, report the unresolved name and ask for a correction or mapping.

## Suggested response format to the user

When the user asks to run this workflow, return:

1. A short summary of how many announcements were fetched, skipped, parsed, and failed.
2. The generated `banner-data.json` content or a downloadable file when file output is available.
3. A validation summary listing banner IDs, pool types, versions, orders, time ranges, and counts of orange and purple IDs.
4. Any warnings about unresolved localized entries, unresolved UIGF names, or format drift.
