# Serverless Data Lake Analytics Pipeline (AWS Athena, Glue, CloudFormation & IAM)

An end-to-end serverless data engineering pipeline modeled on **AWS Academy Data Engineering (Module 4)**, demonstrating how to catalog, query, optimize, and govern multi-file datasets stored in Amazon S3—complete with a **100% local DuckDB & Apache Parquet execution harness** for zero-cost reproducibility.

## Architecture Overview

```text
+-------------------+      +-----------------------+      +-------------------------+
|   Amazon S3       | ---> | AWS Glue Data Catalog | ---> |     Amazon Athena       |
| (Raw CSV & Bucket |      | (Schema & Partition   |      | (Serverless SQL, CTAS,  |
|  Zones)           |      |  Metadata)            |      |  & Analytical Views)    |
+-------------------+      +-----------------------+      +-------------------------+
                                                                       |
                           +-----------------------+                   v
                           | AWS CloudFormation &  |      +-------------------------+
                           | IAM Least-Privilege   | ---> | Reusable Named Queries  |
                           | Policy                |      | & Team Access Control   |
                           +-----------------------+      +-------------------------+