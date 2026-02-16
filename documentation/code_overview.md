# Code Overview

This file is an onboarding walkthrough for the codebase.
It explains what each file is, what it does, and gives brief line-range comments in top-to-bottom order.

Scope:
- Covers Python and JavaScript source files in `app/`, `recommender/`, `utils/`, plus `main.py`.
- Line comments are grouped by contiguous ranges so we can document most lines without turning this into a duplicate of the source.

## app/repos/dnr.py
What this file is:
- Repository layer for the `user_dnr` table (Do Not Recommend list).

What it does:
- Reads DNR rows for a user.
- Inserts/removes DNR entries.
- Resolves IDs against `manga_map` and `manga_merged` for display-safe keys.

Line comments:
- L1-L2: Imports shared DB connector (`get_db`).
- L4-L10: Builds SQL ordering mode (`chron` vs `alpha`).
- L11-L37: `list_by_user` joins DNR rows with metadata and canonical IDs.
- L39-L54: `add` removes possible duplicates, then inserts canonicalized DNR row.
- L56-L67: `remove` deletes by canonical/mangadex/raw ID match.
- L69-L84: `list_manga_ids_by_user` returns normalized key list for fast exclusion.

## app/repos/manga.py
What this file is:
- Repository layer for manga lookup/search and ID resolution.

What it does:
- Handles title search and details fetch from merged and stats sources.
- Resolves ambiguous references (`mal:123`, title, mdex ID) into canonical IDs.

Line comments:
- L1-L2: Imports DB accessor.
- L4-L29: `search_by_title` performs LIKE search over major title fields.
- L31-L38: `get_by_id` fetches one merged row by mangadex ID.
- L40-L50: `get_by_title` exact-match lookup across title fields.
- L52-L63: `get_stats_by_mal_id` fetches MAL stats row.
- L65-L76: `get_stats_by_title` exact-match lookup in stats table.
- L78-L98: `resolve_manga_ref` handles `mal:` input and map lookup.
- L99-L128: Resolves direct mdex ID or unique title match in merged data.
- L129-L147: Resolves unique MAL stats match and builds canonical key.
- L148: Returns safe fallback when no strong match exists.

## app/repos/profile.py
What this file is:
- Repository layer for user profile/preferences/history fields.

What it does:
- Reads/writes profile basics.
- Updates username across linked user-owned tables.
- Stores serialized preference and signal maps.

Line comments:
- L1-L2: Imports DB and dict parsing helper.
- L5-L10: `_coerce_counts` normalizes history structures to dict form.
- L13-L37: `get_profile` returns normalized profile payload.
- L39-L46: `update_profile` writes age/gender/language fields.
- L48-L68: `update_username` renames user across core ownership tables.
- L70-L77: `set_preferences` persists learned preferred genres/themes.
- L79-L80: `clear_preferences` convenience reset wrapper.
- L83-L90: `clear_history` resets preference and blacklist histories.
- L92-L96: `set_ui_prefs` stores serialized UI settings.
- L98-L105: `set_signal_affinities` stores signal-based affinities.
- L107-L113: `set_blacklist_history` stores learned blacklist counts.

## app/repos/ratings.py
What this file is:
- Repository layer for `user_ratings` CRUD and rating-map reads.

What it does:
- Returns list/rating map for UI and recommender.
- Upserts one rating row per user-title canonical key.
- Deletes ratings by canonical identity.

Line comments:
- L1-L2: Imports DB accessor.
- L4-L16: `list_by_user` chooses SQL ordering strategy.
- L17-L44: Lists ratings joined with mapping/metadata/canonical key fields.
- L46-L71: `list_ratings_map` returns `{canonical_key: rating}` dict.
- L73-L84: `upsert_rating` detects existing row by multiple key forms.
- L85-L100: Performs `INSERT ... ON CONFLICT` update.
- L102-L113: `delete_rating` removes by canonical/mdex/raw key.
- L114-L126: `get_rating_value` reads existing numeric rating if present.

## app/repos/reading_list.py
What this file is:
- Repository layer for `user_reading_list` operations.

What it does:
- Lists reading-list entries with enriched metadata.
- Adds/removes items and updates status.
- Returns normalized keys for exclusion logic.

Line comments:
- L1-L2: Imports DB accessor.
- L4-L10: Builds sort order branch.
- L11-L37: `list_by_user` joins reading rows with metadata and key fallbacks.
- L39-L54: `add` dedupes by canonical key then inserts item.
- L56-L67: `remove` deletes row by canonical/mdex/raw key.
- L69-L84: `list_manga_ids_by_user` returns canonicalized keys.
- L87-L107: `update_status` mutates status and fills missing canonical IDs.

## app/repos/users.py
What this file is:
- Repository layer for user auth identity rows.

What it does:
- Fetches user by username.
- Creates user with defaults.
- Updates password hash.
- Deletes user row.

Line comments:
- L1-L2: Imports DB accessor.
- L4-L7: `get_by_username` case-insensitive lookup.
- L10-L21: `create_user` inserts user with default serialized profile fields.
- L23-L27: `set_password_hash` updates auth credential hash.
- L29-L32: `delete_user` removes username row.

## app/repos/__init__.py
What this file is:
- Package marker for repository modules.

Line comments:
- L1: Empty marker file.

## app/db.py
What this file is:
- Flask request-scoped SQLite connection management.

What it does:
- Opens one DB connection per request in `g`.
- Closes connection during app teardown.

Line comments:
- L1-L2: Imports sqlite and Flask globals.
- L5-L10: `get_db` lazily opens/returns request-scoped connection.
- L13-L16: `close_db` safely closes connection if present.

## app/app.py
What this file is:
- Flask app factory + schema bootstrap + page route registration.

What it does:
- Builds app configuration and database schema compatibility checks.
- Registers blueprints and page routes.
- Serves UI pages under `/shelf`.

Line comments:
- L1-L13: Imports and top-level constants (`BASE_PATH`, admin username constant).
- L15-L18: `_default_db_path` resolves fallback local SQLite path.
- L20-L229: `init_db` creates missing tables/indexes for app data.
- L230-L304: `init_db` applies additive schema migrations for older DBs.
- L305-L343: Rebuilds `manga_merged` view joining core/map/stats.
- L344-L346: Commits and closes setup connection.
- L348-L361: Session helper guards (`logged in`, `require login`, `require admin`).
- L364-L383: `create_app` builds Flask app, configures DB/secret, registers blueprints.
- L384-L392: Root landing route (`/`).
- L393-L396: App landing route (`/shelf`).
- L398-L402: Login page route.
- L404-L409: Dashboard page route with auth guard.
- L411-L417: Profile page route with cached options.
- L419-L424: Ratings page route.
- L426-L433: Search page route.
- L434-L447: Recommendations page route.
- L448-L456: Admin page route with admin guard.
- L460-L472: DNR and reading-list page routes.
- L474-L477: Logout page route.
- L482-L486: Creates app instance and dev-run entrypoint.

## app/routes/auth.py
What this file is:
- Authentication API blueprint.

What it does:
- Handles register/login/logout.
- Handles account delete and password change.

Line comments:
- L1-L7: Blueprint setup and auth service import.
- L9-L10: Shared JSON error helper.
- L13-L27: `/register` endpoint validates payload and creates user.
- L29-L44: `/login` endpoint validates credentials and sets session user.
- L46-L49: `/logout` clears session.
- L52-L64: `/delete-account` requires auth and removes account.
- L66-L83: `/change-password` validates payload and updates hash.

## app/routes/api.py
What this file is:
- Main application API blueprint used by frontend pages.

What it does:
- Exposes profile, ratings, DNR, reading list, search, details, events, admin, and recommendations endpoints.
- Provides helper utilities for title normalization and payload shaping.

Line comments:
- L1-L18: Imports and blueprint initialization.
- L21-L40: Auth/admin decorators for route protection.
- L45-L50: Safe row value accessor.
- L52-L59: Text normalization helper.
- L61-L73: English-like text detector.
- L75-L93: Picks best synonym variant.
- L96-L114: Caches MAL english-name lookup.
- L117-L140: Computes display title by language and data availability.
- L143-L152: Sanitizes NaN values for JSON serialization.
- L154-L167: Parses list/bool request fields.
- L170-L185: Variant regex and scoring helper.
- L188-L217: Dedupes payload by MAL ID/series identity.
- L220-L223: `/session` endpoint.
- L227-L233: `/ui-prefs` GET.
- L235-L243: `/ui-prefs` PUT merge/write.
- L245-L250: `/profile` GET.
- L253-L289: `/profile` PUT (age/language/username updates).
- L291-L297: `/profile/clear-history` POST.
- L301-L330: `/dnr` GET list rendering payload.
- L332-L344: `/dnr` POST add item + signal recompute.
- L346-L355: `/dnr/<id>` DELETE.
- L357-L386: `/reading-list` GET list rendering payload.
- L388-L401: `/reading-list` POST add item.
- L403-L415: `/reading-list` PUT status update.
- L417-L426: `/reading-list/<id>` DELETE.
- L429-L462: `/ratings` GET list rendering payload.
- L464-L471: `/ratings/map` GET for quick map lookup.
- L473-L493: `/ratings` POST upsert + event logging.
- L495-L504: `/ratings/<id>` DELETE.
- L507-L535: `/manga/search` GET.
- L537-L619: `/manga/browse` GET filtered browse endpoint.
- L621-L653: `/manga/details` GET with mdex/MAL fallback logic.
- L655-L672: `/events` POST click/details logging.
- L674-L687: `/admin/switch-user` POST.
- L689-L697: `/admin/model-snapshot` GET.
- L699-L716: `/admin/ratings/export` GET CSV output.
- L718-L741: `/admin/ratings/import` POST CSV ingestion.
- L743-L794: `/recommendations` POST scored recommendation payload.

## app/routes/__init__.py
What this file is:
- Package marker for route modules.

Line comments:
- L1: Empty marker file.

## app/services/auth.py
What this file is:
- Business logic layer for auth operations.

What it does:
- Normalizes usernames.
- Handles register/login/password change/delete logic.

Line comments:
- L1-L4: Password hashing and users repo imports.
- L6-L7: Username normalization helper.
- L10-L24: `register` handles new user creation and claim-path for legacy users without password.
- L26-L40: `login` validates credentials and returns normalized user payload.
- L42-L57: `change_password` verifies old password and stores new hash.
- L60-L66: `delete_account` deletes user after existence check.

## app/services/dnr.py
What this file is:
- Service layer orchestrating DNR operations.

What it does:
- Normalizes user IDs and manga references.
- Maintains exclusivity between DNR, ratings, and reading list.

Line comments:
- L1-L4: Imports DNR/manga/ratings/reading repos.
- L7-L8: Username normalization helper.
- L11-L13: Pass-through list call.
- L15-L27: `add_item` resolves canonical ID, writes DNR, removes from other lists.
- L30-L38: `remove_item` resolves canonical ID and deletes.
- L41-L42: Returns canonical DNR keys for exclusion logic.

## app/services/profile.py
What this file is:
- Service layer for profile and preference-history behavior.

What it does:
- Coordinates profile updates/rename.
- Maintains rolling preference caches from request history.

Line comments:
- L1-L7: Imports JSON/DB/repos/parsers.
- L9-L10: Username normalization helper.
- L13-L18: Basic get/update wrappers.
- L21-L35: `change_username` validates and delegates rename.
- L38-L45: `clear_history` resets profile history and request caches.
- L47-L62: `increment_preferences` adjusts preferred genre/theme counters.
- L64-L73: UI preference get/set wrappers.
- L75-L77: Signal affinity write wrapper.
- L79-L98: Increments blacklist history counters.
- L100-L121: Inserts request history snapshot row.
- L123-L150: Reads cache and applies positive deltas.
- L152-L170: Trims history over `max_requests` by removing oldest entries.
- L172-L195: Upserts request cache aggregates.
- L196-L210: Mirrors aggregate counts back to `users` table.

## app/services/ratings.py
What this file is:
- Service layer for rating logic and validation.

What it does:
- Normalizes IDs, validates rating ranges, and performs canonical upsert.
- Enforces list exclusivity with DNR/reading list.

Line comments:
- L1-L4: Imports repos used by rating flow.
- L7-L8: Username normalization helper.
- L11-L17: Read wrappers (`list_ratings`, `list_ratings_map`).
- L19-L38: `set_rating` validates IDs and boolean flags.
- L39-L51: Handles null ratings and numeric bounds.
- L52-L66: Upserts rating then removes same title from DNR/reading list.
- L69-L76: `delete_rating` canonicalizes ref and deletes row.

## app/services/reading_list.py
What this file is:
- Service layer for reading list behavior.

What it does:
- Adds/removes/updates reading entries with canonical IDs.
- Keeps title exclusive across reading list, ratings, and DNR.

Line comments:
- L1-L4: Imports reading/manga/ratings/dnr repos.
- L7-L8: Username normalization helper.
- L11-L13: Read wrapper.
- L15-L34: `add_item` canonicalizes ref, inserts row, removes from other lists.
- L37-L45: `remove_item` canonicalizes ref and deletes.
- L48-L49: Returns canonical reading-list keys.
- L52-L63: `update_status` validates allowed statuses and updates row.

## app/services/recommendations.py
What this file is:
- High-level recommendation service and dataset cache manager.

What it does:
- Loads/caches manga dataset and encoders.
- Applies profile-based filtering, scoring, and explanation text.
- Returns final recommendation payload for API layer.

Line comments:
- L1-L20: Imports and process-level caches.
- L23-L35: `_english_like` helper.
- L37-L56: Cached MAL english-name lookup.
- L58-L71: Chooses fallback synonym title.
- L73-L87: Computes display title by user language.
- L89-L122: Builds map of highest-rated examples per genre/theme.
- L124-L165: Generates human-readable reasons for each recommendation.
- L167-L194: Diversifies repetitive reason phrasing.
- L196-L205: Resolves DB path with env/relative handling.
- L207-L214: Parses year from date-like fields.
- L217-L270: Loads dataframe from `manga_merged` and normalizes list/year fields.
- L272-L330: Builds feature cache (MLBs, matrices, indices, NSFW mask).
- L332-L348: TTL cache getter for expensive feature cache.
- L350-L360: Returns cached available genres/themes.
- L363-L511: Main `recommend_for_user` pipeline (profile fetch, filters, exclusion, scoring, reasons, payload).

## app/services/signals.py
What this file is:
- Service for interaction event logging and signal-affinity recomputation.

What it does:
- Records clicks/details/implicit feedback.
- Computes normalized genre/theme signal vectors from ratings, DNR, reading list, and clicks.

Line comments:
- L1-L15: Imports and weighting constants.
- L17-L26: DB path resolver helper.
- L28-L39: `record_event` writes canonical event row.
- L41-L100: `_fetch_manga_tags` bulk-fetches tags for mdex and MAL IDs.
- L102-L108: Adds weighted contribution to a score map.
- L110-L115: Normalizes weight maps by L1 norm.
- L117-L207: `recompute_affinities` builds weighted tag scores from all interaction sources.
- L209-L216: Event count summary helper.
- L218-L237: Snapshot payload helper for admin debug view.

## app/services/__init__.py
What this file is:
- Package marker for service modules.

Line comments:
- L1: Empty marker file.

## app/__init__.py
What this file is:
- Package marker for app module.

Line comments:
- L1: Empty marker file.

## recommender/constants.py
What this file is:
- Tunable weights and thresholds for scoring.

What it does:
- Defines how much each signal contributes to match score.

Line comments:
- L1-L6: Requested/history/rated-title weight constants.
- L8: Match vs internal blend weight.
- L10-L11: Novelty blending weight.
- L13-L17: Signal weights and personalization ramp thresholds.

## recommender/filtering.py
What this file is:
- Baseline dataframe filtering utilities for recommender.

What it does:
- Applies NSFW, blacklist, read-list, and item-type filters.

Line comments:
- L1-L2: Imports list parser.
- L4-L15: `filter_nsfw` removes explicit content for underage users.
- L17-L24: `parse_lists` converts serialized list fields to lists.
- L26-L33: `filter_already_read` excludes read titles.
- L35-L44: `filter_item_type` filters by selected content types.
- L46-L53: `filter_blacklist` removes genre/theme-blacklisted entries.
- L56-L67: `run_filters` executes filter pipeline in fixed order.

## recommender/recommender.py
What this file is:
- Orchestration wrapper selecting scoring version.

What it does:
- Picks v1/v2/v3 scoring path and forwards options.

Line comments:
- L1-L2: Imports filter/scoring entrypoints.
- L4-L24: Function signature with all scoring options.
- L26-L37: Uses prefiltered dataframe when supplied, else runs filters.
- L38-L70: Chooses v1 or v2 path by mode.
- L71-L89: Defaults to v3 path and returns ranked results.

## recommender/scoring.py
What this file is:
- Core ranking math for v1/v2/v3 recommendation strategies.

What it does:
- Computes match signals, internal score blend, novelty/diversity/reroll behavior.
- Includes vectorized fast path for v3.

Line comments:
- L1-L19: Imports and scoring constants.
- L21-L65: `compute_rating_affinities` (legacy) from explicit ratings.
- L67-L101: `score_row` (legacy per-row scorer).
- L103-L112: `combine_scores` match/internal blending helper.
- L115-L159: `compute_rating_affinities_v2` normalized affinity variant.
- L161-L168: Min-max utility.
- L171-L178: Series key normalization for dedupe/diversity.
- L181-L192: Personalization strength ramp function.
- L194-L197: Soft-cap transform for match score.
- L199-L211: Converts sparse weight dicts to dense vectors.
- L214-L229: Collects rated row indices and ratings.
- L232-L267: Vectorized affinity calculation helper.
- L269-L283: Vectorized earliest-year penalty.
- L284-L293: Year extraction helper.
- L296-L322: DataFrame earliest-year penalty path.
- L325-L342: Novelty blending helper.
- L345-L355: Weighted sampling helper.
- L358-L370: Reroll candidate pool builder.
- L373-L430: Diversity selector to prevent over-clustering.
- L433-L483: v2 per-row score with signal boosts.
- L488-L538: v3 per-row score with similar signal logic.
- L541-L688: `_score_and_rank_v3_fast` vectorized scoring path.
- L691-L793: `score_and_rank_v3` chooses fast path or fallback path.
- L795-L869: `score_and_rank_v2` pipeline.
- L871-L970: `score_and_rank` legacy v1 pipeline.

## recommender/__init__.py
What this file is:
- Package marker for recommender module.

Line comments:
- L1: Empty marker file.

## utils/parsing.py
What this file is:
- Lightweight parsing helpers for serialized lists/dicts.

What it does:
- Parses list-like strings and dict-like strings safely.

Line comments:
- L1-L3: Imports `ast` and pandas null helpers.
- L4-L18: `parse_list` supports literal-eval and comma-split fallback.
- L20-L35: `parse_dict` supports dict passthrough, null handling, and safe parse fallback.

## utils/lookup.py
What this file is:
- Utility for collecting unique tag options.

What it does:
- Extracts and sorts unique values from parsed list columns.

Line comments:
- L1: Imports list parser.
- L3-L10: `get_all_unique` accumulates stripped unique items.
- L11: Returns sorted final option list.

## utils/__init__.py
What this file is:
- Package marker for utils module.

Line comments:
- L1: Empty marker file.

## main.py
What this file is:
- Simple run entrypoint importing Flask app instance.

What it does:
- Starts the Flask development server.

Line comments:
- L1: Imports app object from `app.app`.
- L4-L5: Runs app on host/port with debug enabled.

## app/static/common.js
What this file is:
- Shared frontend utilities used by multiple pages.

What it does:
- Wraps fetch API calls.
- Provides toast UI, nav username loading, safe render helpers, and details modal rendering.

Line comments:
- L1-L6: Base-path helpers for path-safe API/static URL composition.
- L8-L21: Shared `api()` wrapper with JSON decode and error handling.
- L24-L40: Toast notification helper.
- L42-L60: Loads current session user into nav.
- L61-L69: HTML escaping helper.
- L71-L87: List parser for mixed payload formats.
- L89-L102: JSON parser helper for string/object fields.
- L104-L111: Series-key normalizer.
- L113-L137: Client-side dedupe helper by MAL/title key.
- L139-L156: Formatting helpers for language/date labels.
- L158-L173: Chip rendering helper.
- L175-L269: `renderDetailsHTML` builds modal HTML for detailed view.
- L271-L315: Modal creation/open behavior and exported globals.

## app/static/login.js
What this file is:
- Login/register page script.

What it does:
- Sends login/register requests and redirects to dashboard.

Line comments:
- L1-L5: DOM node references.
- L7-L10: Status message helper.
- L13-L17: Enter key triggers login.
- L18-L27: Login request and redirect flow.
- L29-L38: Register request flow.
- L40-L44: Event bindings for buttons/Enter key.

## app/static/dashboard.js
What this file is:
- Dashboard summary script.

What it does:
- Fetches profile/ratings/DNR/reading counts and renders one-line summary.

Line comments:
- L1: Summary DOM node lookup.
- L3-L19: `loadSummary` fetches four endpoints and builds summary text.
- L21: Executes on load.

## app/static/profile.js
What this file is:
- Profile page script.

What it does:
- Loads profile fields/history chips.
- Saves profile updates, clears history, changes password, deletes account.

Line comments:
- L1-L15: DOM references.
- L17-L20: Status helper.
- L22-L33: History-chip renderer.
- L35-L46: `loadProfile` fetches and populates form/history.
- L48-L62: `saveProfile` writes updates and refreshes UI.
- L64-L69: Clears profile history.
- L72-L80: Delete-account confirm and redirect.
- L82-L93: Password-change flow.
- L95-L102: Event listeners and initial load call.

## app/static/dnr.js
What this file is:
- DNR page script.

What it does:
- Loads, filters, displays, and removes DNR items.
- Persists sorting/type UI preferences.

Line comments:
- L1-L12: DOM references and default type set constant.
- L14-L40: Loads saved UI prefs.
- L42-L49: Persists UI prefs.
- L51-L79: Type selection helper functions.
- L81-L90: Search/type filter function.
- L92-L121: Renders DNR cards.
- L123-L133: Details modal fetch/render flow.
- L135-L140: Fetches DNR list by sort mode.
- L142-L176: Type modal open/select/save/close handlers.
- L179-L190: Filter and sort change bindings.
- L192-L206: Card action handlers (details/remove).
- L208: Initial load chain.

## app/static/ratings.js
What this file is:
- Ratings page script.

What it does:
- Loads rating list, filters/sorts, edits/deletes ratings, and opens details.
- Tracks cross-list placement prompts before moving items.

Line comments:
- L1-L33: DOM/state declarations.
- L35-L44: Loads ratings/DNR/reading map for location-awareness.
- L46-L52: Computes location labels per item.
- L54-L80: Type filter helper functions.
- L82-L98: Rate modal open/close helpers.
- L100-L127: Loads ratings page UI prefs.
- L129-L136: Saves UI prefs.
- L138-L141: Loading indicator helper.
- L143-L151: Text/type filter function.
- L154-L185: Renders ratings cards.
- L187-L197: Details fetch/render helper.
- L199-L208: Loads ratings from API.
- L210-L213: Delete rating flow.
- L215-L281: Filter/sort/type-modal event wiring.
- L283-L335: Rate-modal update handlers and close behavior.
- L337-L338: Initial load sequence.

## app/static/reading_list.js
What this file is:
- Reading-list page script.

What it does:
- Loads reading list, filters by text/status/type, updates status, removes, and rates items.

Line comments:
- L1-L21: DOM references and defaults.
- L23-L38: Rate modal open/close helpers.
- L42-L68: Loads saved UI prefs.
- L70-L77: Saves UI prefs.
- L79-L109: Type-selection helper functions.
- L111-L127: Status normalization and filter function.
- L129-L164: Renders reading list cards and status selector.
- L166-L176: Details fetch/render helper.
- L178-L183: Loads reading list data.
- L185-L219: Type modal wiring and rendering refresh.
- L222-L238: Text/status/sort filter event bindings.
- L240-L272: Status update and card-action handlers.
- L275-L306: Rate-modal add/close handlers.
- L307: Initial load call.

## app/static/recommendations.js
What this file is:
- Recommendations page script.

What it does:
- Manages recommendation inputs and toggles.
- Requests recommendations and renders result cards.
- Supports add/rate/details workflows and saves recommendation UI prefs.

Line comments:
- L1-L39: DOM and state declarations.
- L41-L85: Rate/add modal open-close helpers.
- L88-L130: Loads recommendation UI prefs.
- L132-L139: Saves UI prefs.
- L141-L145: Loading indicator helper.
- L147-L162: DOM helpers for selecting/removing cards.
- L164-L196: Recommendation card renderer.
- L198-L243: Input-chip helper functions for genres/themes/blacklists.
- L245-L248: Ratings map loader.
- L250-L276: Recommendation request call and result rendering.
- L278-L296: Details fetch/render helper.
- L298-L376: Input controls and modal toggle event bindings.
- L378-L415: Recommendation trigger and chip-removal bindings.
- L417-L468: Rate modal submit/reading actions.
- L470-L518: Add modal actions for rating/reading/DNR.
- L520-L533: Info modal handlers.
- L535-L550: Card-level details/add action dispatcher.
- L552-L553: Initial loading state and pref fetch.

## app/static/search.js
What this file is:
- Search and browse page script.

What it does:
- Performs title search and browse queries with filters.
- Renders cards, opens details, and supports add/rate actions.
- Tracks where items currently live (ratings/reading/DNR).

Line comments:
- L1-L54: DOM references and state declarations.
- L56-L93: Generic UI helpers and type filtering.
- L95-L121: Cross-list state loading and lookup helpers.
- L123-L150: Add/rate modal open-close helpers.
- L152-L163: Removes item cards from both result sections.
- L165-L195: Card rendering function.
- L197-L236: Browse chip rendering and add helpers.
- L238-L248: Details fetch/render helper.
- L250-L268: Search flow.
- L270-L289: Browse flow.
- L291-L313: UI preference load for search page.
- L315-L322: UI pref save helper.
- L324-L406: Search/browse/type-modal/chip event wiring.
- L408-L423: Shared list click-handler attach helper.
- L425-L427: Attach click handlers to search+browse lists.
- L428-L496: Add-modal actions for rate/reading/DNR.
- L498-L537: Rate-modal actions and modal close handling.
- L539-L540: Initial pref and list-state loads.

## app/static/admin.js
What this file is:
- Admin page script.

What it does:
- Supports admin user switch and CSV rating import.

Line comments:
- L1-L6: DOM references.
- L8-L11: Status helper.
- L13-L22: User switch API call.
- L24-L32: CSV import API call.
- L34-L35: Button event bindings.

