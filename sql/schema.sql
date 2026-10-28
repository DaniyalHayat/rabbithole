PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS papers (
 id TEXT PRIMARY KEY, title TEXT NOT NULL CHECK(length(title)>0),
 year INTEGER CHECK(year BETWEEN 1600 AND 2026), doi TEXT,
 abstract TEXT NOT NULL, kind TEXT NOT NULL, open_access INTEGER NOT NULL CHECK(open_access IN(0,1)),
 retracted INTEGER NOT NULL CHECK(retracted IN(0,1)), citations INTEGER NOT NULL CHECK(citations>=0)
);
CREATE TABLE IF NOT EXISTS topics(id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS paper_topics(paper_id TEXT REFERENCES papers(id), topic_id TEXT REFERENCES topics(id), PRIMARY KEY(paper_id,topic_id));
CREATE TABLE IF NOT EXISTS citations(source_id TEXT REFERENCES papers(id), target_id TEXT REFERENCES papers(id), PRIMARY KEY(source_id,target_id), CHECK(source_id<>target_id));
CREATE TABLE IF NOT EXISTS provenance(paper_id TEXT REFERENCES papers(id), source_file TEXT, theme TEXT, PRIMARY KEY(paper_id,source_file));
CREATE VIRTUAL TABLE IF NOT EXISTS paper_search USING fts5(id UNINDEXED,title,abstract,tokenize='unicode61');
CREATE TABLE IF NOT EXISTS paper_countries(paper_id TEXT REFERENCES papers(id), country_code TEXT CHECK(length(country_code)=2), PRIMARY KEY(paper_id,country_code));
CREATE VIEW IF NOT EXISTS topic_coverage AS SELECT t.name, count(*) papers FROM topics t JOIN paper_topics pt ON pt.topic_id=t.id GROUP BY t.id;
CREATE VIEW IF NOT EXISTS citation_degrees AS SELECT p.id,p.title,count(c.target_id) out_degree FROM papers p LEFT JOIN citations c ON c.source_id=p.id GROUP BY p.id;
