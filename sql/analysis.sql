-- Reconcile accepted records and citation integrity.
SELECT count(*) AS papers, sum(open_access) AS open_papers, sum(retracted) AS retractions FROM papers;
SELECT name, papers FROM topic_coverage ORDER BY papers DESC LIMIT 20;
SELECT p.year, count(*) AS papers FROM papers p GROUP BY p.year ORDER BY p.year;
-- References are directed; a citation is not evidence that the citing author agrees.
SELECT p.title, count(*) AS incoming FROM citations c JOIN papers p ON p.id=c.target_id GROUP BY p.id ORDER BY incoming DESC LIMIT 10;
-- FTS query values must be bound parameters, never string-interpolated SQL.
SELECT id, title, bm25(paper_search) AS score FROM paper_search WHERE paper_search MATCH 'music memory' ORDER BY score LIMIT 10;
-- Each paper-country pair is unique; international collaborations are non-additive.
SELECT country_code,count(*) AS snapshot_papers FROM paper_countries pc JOIN papers p ON p.id=pc.paper_id WHERE p.retracted=0 GROUP BY country_code ORDER BY snapshot_papers DESC;
