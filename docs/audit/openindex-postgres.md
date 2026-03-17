CREATE INDEX
CREATE INDEX
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE FUNCTION
CREATE TRIGGER
CREATE VIEW
2026-03-17 16:11:07.066 UTC [54] ERROR:  column "files.size" must appear in the GROUP BY clause or be used in an aggregate function at character 800
2026-03-17 16:11:07.066 UTC [54] STATEMENT:  CREATE OR REPLACE VIEW file_size_distribution AS
	SELECT 
	    CASE 
	        WHEN size < 1024 THEN '< 1 KB'
	        WHEN size < 1024*1024 THEN '1 KB - 1 MB'
	        WHEN size < 1024*1024*10 THEN '1 MB - 10 MB'
	        WHEN size < 1024*1024*100 THEN '10 MB - 100 MB'
	        WHEN size < 1024*1024*1024 THEN '100 MB - 1 GB'
	        ELSE '> 1 GB'
	    END as size_category,
	    COUNT(*) as file_count,
	    SUM(size) as total_size
	FROM files 
	WHERE is_directory = FALSE
	GROUP BY 
	    CASE 
	        WHEN size < 1024 THEN '< 1 KB'
	        WHEN size < 1024*1024 THEN '1 KB - 1 MB'
	        WHEN size < 1024*1024*10 THEN '1 MB - 10 MB'
	        WHEN size < 1024*1024*100 THEN '10 MB - 100 MB'
	        WHEN size < 1024*1024*1024 THEN '100 MB - 1 GB'
	        ELSE '> 1 GB'
	    END
	ORDER BY 
	    CASE 
	        WHEN size < 1024 THEN 1
	        WHEN size < 1024*1024 THEN 2
	        WHEN size < 1024*1024*10 THEN 3
	        WHEN size < 1024*1024*100 THEN 4
	        WHEN size < 1024*1024*1024 THEN 5
	        ELSE 6
	    END;

PostgreSQL Database directory appears to contain a database; Skipping initialization

