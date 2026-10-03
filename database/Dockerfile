FROM pgvector/pgvector:pg16

# Copy database initialization SQL script into docker-entrypoint-initdb.d
COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 5432
