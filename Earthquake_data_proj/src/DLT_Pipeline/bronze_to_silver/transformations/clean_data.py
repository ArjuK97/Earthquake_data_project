import dlt

from pyspark.sql.functions import (
    col,
    explode,
    from_unixtime,
    from_json, 
    current_timestamp
)
from pyspark.sql.types import *

volume_path = "/Volumes/geo_proj/bronze/earthquake_data"

primary_key=["id"]
feature_schema = StructType([
    StructField("id", StringType()),
    StructField("type", StringType()),
    StructField("properties", StructType([
        StructField("mag", DoubleType()),
        StructField("place", StringType()),
        StructField("time", LongType()),
        StructField("status", StringType()),
        StructField("tsunami", LongType()),
        StructField("felt", LongType()),
        StructField("sig", LongType()),
        StructField("nst", LongType()),
        StructField("url", StringType()),
        StructField("detail", StringType()),
        StructField("cdi", DoubleType()),
        StructField("mmi", DoubleType()),
        StructField("alert", StringType()),
        StructField("net", StringType()),
        StructField("code", StringType()),
        StructField("ids", StringType()),
        StructField("sources", StringType()),
        StructField("types", StringType()),
        StructField("dmin", DoubleType()),
        StructField("rms", DoubleType()),
        StructField("gap", DoubleType()),
        StructField("magType", StringType()),
        StructField("title", StringType())
    ])),
    StructField("geometry", StructType([
        StructField("type", StringType()),
        StructField("coordinates", ArrayType(DoubleType()))
    ]))
])

@dlt.view(name="earthquake_data_view")
def earthquake_data():
    df = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.includeExistingFiles", "true")
        .option("multiLine", "true")
        .load(volume_path)
    )
        
    df = df.withColumn("_load_timestamp", current_timestamp())
    df = df.withColumn("features_parsed", from_json(col("features"), ArrayType(feature_schema)))
    df = df.select(explode(col("features_parsed")).alias("feature"), "_load_timestamp")
    df = df.select(
        "feature.properties.*",
        "feature.id",
        col("feature.geometry.coordinates")[0].alias("longitude"),
        col("feature.geometry.coordinates")[1].alias("latitude"),
        col("feature.geometry.coordinates")[2].alias("depth"),
        "_load_timestamp"
    )
    df = df.withColumn("time", from_unixtime(col("time") / 1000).cast("timestamp"))
    df = df.withColumn("mag", col("mag").cast("double"))
    df = df.withColumn("nst", col("nst").cast("double"))
    df = df.withColumn("sig", col("sig").cast("double"))
    df = df.withColumn("tsunami", col("tsunami").cast("double"))
    df = df.withColumn("felt", col("felt").cast("double"))

    return df

dlt.create_streaming_table(name="earthquake_data_final")

dlt.apply_changes(
    target="earthquake_data_final",
    source="earthquake_data_view",
    keys=primary_key,
    sequence_by="_load_timestamp",
    stored_as_scd_type='1')    