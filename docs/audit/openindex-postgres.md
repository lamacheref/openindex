openindex-postgres  | 
openindex-postgres  |     pg_ctl -D /var/lib/postgresql/data -l logfile start
openindex-postgres  | 
openindex-postgres  | initdb: warning: enabling "trust" authentication for local connections
openindex-postgres  | initdb: hint: You can change this by editing pg_hba.conf or using the option -A, or --auth-local and --auth-host, the next time you run initdb.
openindex-postgres  | waiting for server to start....2026-03-17 14:40:58.863 UTC [41] LOG:  starting PostgreSQL 17.9 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
openindex-postgres  | 2026-03-17 14:40:58.864 UTC [41] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
openindex-postgres  | 2026-03-17 14:40:58.867 UTC [44] LOG:  database system was shut down at 2026-03-17 14:40:58 UTC
openindex-postgres  | 2026-03-17 14:40:58.869 UTC [41] LOG:  database system is ready to accept connections
openindex-postgres  |  done
openindex-postgres  | server started
openindex-postgres  | CREATE DATABASE
openindex-postgres  | 
openindex-postgres  | 
openindex-postgres  | /usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/init.sql
openindex-postgres  | CREATE EXTENSION
openindex-postgres  | CREATE EXTENSION
openindex-postgres  | CREATE TABLE
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE TABLE
openindex-postgres  | CREATE TABLE
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE TABLE
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE TABLE
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE INDEX
openindex-postgres  | CREATE FUNCTION
openindex-postgres  | CREATE TRIGGER
openindex-postgres  | CREATE VIEW
openindex-postgres  | 2026-03-17 14:40:59.050 UTC [54] ERROR:  column "files.size" must appear in the GROUP BY clause or be used in an aggregate function at character 520
openindex-postgres  | 2026-03-17 14:40:59.050 UTC [54] STATEMENT:  CREATE OR REPLACE VIEW file_size_distribution AS
openindex-postgres  | 	SELECT 
openindex-postgres  | 	    CASE 
openindex-postgres  | 	        WHEN size < 1024 THEN '< 1 KB'
openindex-postgres  | 	        WHEN size < 1024*1024 THEN '1 KB - 1 MB'
openindex-postgres  | 	        WHEN size < 1024*1024*10 THEN '1 MB - 10 MB'
openindex-postgres  | 	        WHEN size < 1024*1024*100 THEN '10 MB - 100 MB'
openindex-postgres  | 	        WHEN size < 1024*1024*1024 THEN '100 MB - 1 GB'
openindex-postgres  | 	        ELSE '> 1 GB'
openindex-postgres  | 	    END as size_category,
openindex-postgres  | 	    COUNT(*) as file_count,
openindex-postgres  | 	    SUM(size) as total_size
openindex-postgres  | 	FROM files 
openindex-postgres  | 	WHERE is_directory = FALSE
openindex-postgres  | 	GROUP BY size_category
openindex-postgres  | 	ORDER BY 
openindex-postgres  | 	    CASE 
openindex-postgres  | 	        WHEN size < 1024 THEN 1
openindex-postgres  | 	        WHEN size < 1024*1024 THEN 2
openindex-postgres  | 	        WHEN size < 1024*1024*10 THEN 3
openindex-postgres  | 	        WHEN size < 1024*1024*100 THEN 4
openindex-postgres  | 	        WHEN size < 1024*1024*1024 THEN 5
openindex-postgres  | 	        ELSE 6
openindex-postgres  | 	    END;
openindex-postgres  | psql:/docker-entrypoint-initdb.d/init.sql:150: ERROR:  column "files.size" must appear in the GROUP BY clause or be used in an aggregate function
openindex-postgres  | LINE 18:         WHEN size < 1024 THEN 1
openindex-postgres  |                       ^
openindex-postgres  | 
openindex-postgres  | PostgreSQL Database directory appears to contain a database; Skipping initialization
openindex-postgres  | 
openindex-postgres  | 2026-03-17 14:40:59.310 UTC [1] LOG:  starting PostgreSQL 17.9 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
openindex-postgres  | 2026-03-17 14:40:59.310 UTC [1] LOG:  listening on IPv4 address "0.0.0.0", port 5432
openindex-postgres  | 2026-03-17 14:40:59.310 UTC [1] LOG:  listening on IPv6 address "::", port 5432
openindex-postgres  | 2026-03-17 14:40:59.312 UTC [1] LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
openindex-postgres  | 2026-03-17 14:40:59.314 UTC [29] LOG:  database system was interrupted; last known up at 2026-03-17 14:40:58 UTC
openindex-postgres  | 2026-03-17 14:40:59.332 UTC [29] LOG:  database system was not properly shut down; automatic recovery in progress
openindex-postgres  | 2026-03-17 14:40:59.333 UTC [29] LOG:  redo starts at 0/14ED240
openindex-postgres  | 2026-03-17 14:40:59.342 UTC [29] LOG:  invalid record length at 0/1955C68: expected at least 24, got 0
openindex-postgres  | 2026-03-17 14:40:59.342 UTC [29] LOG:  redo done at 0/1955A60 system usage: CPU: user: 0.00 s, system: 0.00 s, elapsed: 0.00 s
openindex-postgres  | 2026-03-17 14:40:59.345 UTC [27] LOG:  checkpoint starting: end-of-recovery immediate wait
openindex-postgres  | 2026-03-17 14:40:59.365 UTC [27] LOG:  checkpoint complete: wrote 976 buffers (6.0%); 0 WAL file(s) added, 0 removed, 0 recycled; write=0.009 s, sync=0.009 s, total=0.021 s; sync files=339, longest=0.002 s, average=0.001 s; distance=4514 kB, estimate=4514 kB; lsn=0/1955C68, redo lsn=0/1955C68
openindex-postgres  | 2026-03-17 14:40:59.371 UTC [1] LOG:  database system is ready to accept connections
openindex-postgres  | 2026-03-17 14:41:07.615 UTC [43] ERROR:  function calculate_duplicates() does not exist at character 8
openindex-postgres  | 2026-03-17 14:41:07.615 UTC [43] HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
openindex-postgres  | 2026-03-17 14:41:07.615 UTC [43] STATEMENT:  SELECT calculate_duplicates()
openindex-postgres  | 2026-03-17 14:41:10.100 UTC [47] ERROR:  function calculate_duplicates() does not exist at character 8
openindex-postgres  | 2026-03-17 14:41:10.100 UTC [47] HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
openindex-postgres  | 2026-03-17 14:41:10.100 UTC [47] STATEMENT:  SELECT calculate_duplicates()
openindex-postgres  | 2026-03-17 14:41:12.610 UTC [51] ERROR:  function calculate_duplicates() does not exist at character 8
openindex-postgres  | 2026-03-17 14:41:12.610 UTC [51] HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
openindex-postgres  | 2026-03-17 14:41:12.610 UTC [51] STATEMENT:  SELECT calculate_duplicates()
openindex-postgres  | 2026-03-17 14:41:16.307 UTC [55] ERROR:  function calculate_duplicates() does not exist at character 8
openindex-postgres  | 2026-03-17 14:41:16.307 UTC [55] HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
openindex-postgres  | 2026-03-17 14:41:16.307 UTC [55] STATEMENT:  SELECT calculate_duplicates()
openindex-postgres  | 2026-03-17 14:41:19.439 UTC [59] ERROR:  function calculate_duplicates() does not exist at character 8
openindex-postgres  | 2026-03-17 14:41:19.439 UTC [59] HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
openindex-postgres  | 2026-03-17 14:41:19.439 UTC [59] STATEMENT:  SELECT calculate_duplicates()
