# CSE 694 Slideshow Outline (Stage 1 -> Stage 2 -> Stage 3)

This outline is designed to map directly to your proposal commitments and your current notebook results.

## Slide 1: Title + Problem
- Project title: Graph-Based Manga Recommendation System.
- One-line problem: content-only ranking misses relational structure between users and manga.
- One-line goal: move from heuristic content ranking to graph link prediction, then to learned graph representations.

## Slide 2: What Already Existed Before This Stage
- Flask web app with auth, profile, ratings, reading list, DNR, search, recommendations, and admin pages.
- SQLite-backed data pipeline with `manga_core`, `manga_stats`, `manga_map`, and `manga_merged`.
- Existing content-based recommender baseline (v1/v2/v3) already running in app.
- This is your Stage 1 baseline system and experimentation foundation.

## Slide 3: Stage 2 Objective (From Proposal)
- Apply graph-based link prediction techniques using neighborhood overlap.
- Methods required by proposal: Jaccard similarity and Adamic-Adar.
- Evaluate with Precision@K, Recall@K, and NDCG.
- Deliver construction pipeline + baseline + graph recommenders + experimental evaluation.

## Slide 4: Stage 2 Graph Construction Pipeline (Completed)
- Data loaded from SQLite into notebook workflow.
- Heterogeneous graph built with nodes: user, manga, genre, theme, author.
- Edge types built: rated, plans_to_read, in_progress, avoid, has_genre, has_theme, written_by.
- Graph schema and edge/node counts are generated as reproducible notebook outputs.

## Slide 5: Stage 2 Graph Recommenders Implemented (Completed)
- Implemented overlap-based heuristics:
- Common Neighbors.
- Jaccard similarity.
- Adamic-Adar index.
- Ranking done over candidate manga using user seed profiles and metadata overlap.

## Slide 6: Stage 2 Baselines Implemented (Completed)
- Content baseline: `content_v3` from existing system.
- Additional sanity baseline: popularity ranking.
- Shared evaluation protocol used across methods for fair comparison.

## Slide 7: Stage 2 Evaluation Protocol (Completed)
- Offline leave-one-out style user split with repeated random seeds.
- Candidate set uses held-out positives plus sampled unseen negatives.
- Metrics reported: Precision@K, Recall@K, NDCG@K.
- Additional diagnostics: HitRate@K, MRR, first-hit rank.

## Slide 8: Stage 2 Proposal Checklist Status
- Graph link prediction methods applied (Jaccard + Adamic-Adar): Yes.
- Evaluation with Precision@K / Recall@K / NDCG: Yes.
- Construction pipeline delivered: Yes.
- Baseline + graph recommenders delivered: Yes.
- Experimental evaluation delivered: Yes.
- Presentation materials: this slideshow.

## Slide 9: Stage 2 Results Summary
- Main finding: graph-overlap heuristics underperform `content_v3` and popularity on current sparse user data.
- Interpretation: negative result is still valid and informative.
- Conclusion: simple local-overlap heuristics are likely too weak for this data regime.

## Slide 10: Why Stage 3 Is Needed
- Sparse and limited in-house user interactions constrain heuristic link prediction quality.
- Need representation learning that captures higher-order structure beyond local overlap.
- Stage 3 target: learned embeddings over user-item graph.

## Slide 11: Stage 3 Plan (Technical)
- Add external user interaction data (real ratings) into a separate experimental ingestion path.
- Keep production app tables untouched; store external interactions in dedicated experiment tables.
- Align items by `mal_id` first, then map to MangaDex IDs via existing map logic where possible.
- Build Stage 3 model candidates:
- Random-walk node embeddings (DeepWalk/Node2Vec style).
- Optional graph neural model extension if time permits.

## Slide 12: Stage 3 Data Integration Plan
- Source: free MyAnimeList-like user-item rating dataset with user IDs and item IDs.
- Ingest table proposal: `external_user_ratings(user_id, mal_id, rating, timestamp, source)`.
- Quality filters:
- minimum ratings per user.
- minimum ratings per item.
- remove extreme sparsity rows.
- Split protocol mirrors Stage 2 so metrics remain comparable.

## Slide 13: Stage 3 Evaluation Plan
- Reuse same ranking metrics: Precision@K, Recall@K, NDCG@K.
- Compare Stage 3 embeddings against Stage 2 best methods (`content_v3`, popularity, best graph heuristic).
- Report mean and spread across seeds/users.
- Include ablations: embedding dimension, walk length, context window, negative sampling settings.

## Slide 14: Risks + Mitigations
- Risk: ID alignment gaps between external dataset and local catalog.
- Mitigation: strict `mal_id` join and track mapped/unmapped coverage.
- Risk: noisy external users/items.
- Mitigation: activity thresholds and filtering.
- Risk: overclaiming from small local sample.
- Mitigation: clearly separate local-only results and external-data experiments.

## Slide 15: Final Close
- Stage 2 was completed according to proposal scope and deliverables.
- Stage 2 results justified the move to Stage 3.
- Stage 3 goal: improve ranking quality through learned graph representations with richer user interaction data.

## Optional Backup Slides
- Full graph schema table screenshot.
- Metric table screenshot from notebook.
- Per-method plot screenshots.
- External data ingestion schema draft.
