# Retail Sales HDFS Storage Optimization

Local HDFS implementation of a storage strategy for a retail company collecting
daily CSV sales files from 500 stores, plus a translation of the same design
onto Databricks Free Edition / Microsoft Fabric. Part of the EY Data
Engineering training portfolio.

## Status

- [x] Design decisions finalized (directory hierarchy, block size, replication factor)
- [x] Docker Compose HDFS cluster defined (1 NameNode + 2 DataNodes)
- [x] Sample data generator built
- [ ] Cluster verified running (2/2 live DataNodes)
- [ ] Sample data generated
- [ ] HDFS directories created
- [ ] Files uploaded with custom block size + replication
- [ ] Storage metrics verified (`du -h`, `fsck`, NameNode UI screenshots)
- [ ] Cloud translation writeup (Databricks Free Edition / Microsoft Fabric)

*(This checklist is the source of truth for what's actually done — update it as
each phase is verified, not before.)*

## Scenario

A retail company collects daily sales data from 500 stores. Each store
generates one CSV (~100 MB) of transaction details per day. The goal is an
HDFS storage layout that's organized for downstream analytics and efficient
given the file sizes involved.

## Architecture

A local 3-container Hadoop cluster, run via Docker Compose:

- **1 NameNode** — metadata, block map, web UI on port 9870
- **2 DataNodes** — actual block storage, web UI on port 9864 (and 9865 for the second, remapped)

Two DataNodes (not three) is deliberate: it's enough to make replication
factor a real, checkable decision instead of a theoretical one — see
"Replication factor" below.

## Repo Structure

```
hdfs-storage-optimization/
├── docker-compose.yml
├── hadoop.env
├── data-generator/
│   └── generate_sales_data.py
├── sample_data/            # generated locally, gitignored
├── docs/
│   └── screenshots/        # NameNode UI evidence
└── README.md
```

## Setup

```powershell
docker compose up -d
docker compose ps          # all 3 containers should show "Up"
```

Verify at http://localhost:9870 → Datanodes tab → should show 2 live nodes.

```powershell
cd data-generator
python -m venv venv
venv\Scripts\activate
pip install faker
python generate_sales_data.py
```

## Design Decisions

### Directory hierarchy: `/sales_data/<year>/<month>/<day>/<store_id>/`

Partitions by the dimensions analytics queries actually filter on — date
range and store — so downstream engines (Spark, Hive) can prune partitions
instead of scanning the full dataset.

### Block size: 256 MB (vs. 128 MB default)

Individual store files (~100 MB) already fit inside the 128 MB default, so
the case for a larger block size isn't about a single file — it's about:
- **Headroom for growth**: peak-season files can exceed 100 MB without
  fragmenting into a second block.
- **Fewer, larger blocks at scale**: across 500 stores × 365 days × multiple
  years, and especially once daily files get compacted into monthly rollups,
  a larger block size keeps NameNode metadata (which lives entirely in RAM)
  from growing faster than it needs to.
- **Fewer partitions per file for batch scans**: Spark/MapReduce splits
  roughly align with block boundaries, so fewer blocks per file means less
  per-task scheduling overhead on full historical scans.

Demonstrated concretely with one ~150 MB "peak day" sample file: at the 128 MB
default it splits into 2 blocks; at 256 MB it stays as 1 — visible directly
in `hdfs fsck -files -blocks`.

### Replication factor: 2 (vs. 3 default)

This cluster only has 2 DataNodes, so a replication factor of 3 can never
fully satisfy itself — those blocks show as under-replicated in `fsck`.
Setting replication explicitly to 2 for this analytical dataset matches
actual cluster capacity, still tolerates a single DataNode failure, and
avoids wasting write bandwidth/storage on a replica the cluster can't place
anyway. (This data is also treated as temporary/re-derivable — not the kind
of dataset that needs 3x durability.)

## Verification Evidence (Phase 2 — pending)

*To be filled in after upload: `hdfs dfs -du -h` output, `hdfs fsck` block
report, and NameNode UI screenshots go here / in `docs/screenshots/`.*

## Cloud Translation (Phase 3 — pending)

*Mapping of this design onto Databricks Free Edition (Unity Catalog Volumes)
and Microsoft Fabric (OneLake) goes here — how directory partitioning, block
size, and replication concepts translate (or don't) onto managed cloud
storage.*

## Tech Stack

Docker Desktop, Hadoop 3.2.1 (`bde2020/hadoop-namenode` / `hadoop-datanode`),
Python 3 + Faker for sample data generation.
