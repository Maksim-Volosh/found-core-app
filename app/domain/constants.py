# Largest value a Postgres BIGINT column (every id here) can hold.
MAX_INT64 = 2**63 - 1

# Length of every stored embedding. The `vector(1536)` column type depends on it, so it is not configurable.
EMBEDDING_DIMENSIONS = 1536
