import argparse
import os
import time
import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, avg, col, regexp_replace, countDistinct
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


def guardar_csv_pandas(df, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")


def limpiar_pandas(df):
    df["DATO_NUMERICO"] = df["DATO_NUMERICO"].astype(str).str.replace(",", ".", regex=False)
    df["DATO_NUMERICO"] = pd.to_numeric(df["DATO_NUMERICO"], errors="coerce")
    df = df.dropna(subset=["DATO_NUMERICO", "MUNICIPIO", "YEAR"])
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--escenario", default="Procesamiento local")
    parser.add_argument("--factor", type=int, default=1)
    parser.add_argument("--master", default="local[*]")
    args = parser.parse_args()

    inicio_total = time.time()

    spark = SparkSession.builder.appName("Seguridad_Cundinamarca_PySpark").master(args.master).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    df_original = spark.read.csv("data/seguridad_clean.csv", header=True, inferSchema=True)

    registros_originales = df_original.count()

    df = df_original.withColumn(
        "DATO_NUMERICO",
        regexp_replace(col("DATO_NUMERICO").cast("string"), ",", ".")
    )

    df = df.withColumn(
        "DATO_NUMERICO",
        col("DATO_NUMERICO").cast("double")
    )

    df = df.dropna(subset=["DATO_NUMERICO", "MUNICIPIO", "YEAR"])

    if args.factor > 1:
        replicas = spark.range(args.factor).withColumnRenamed("id", "REPLICA")
        df = df.crossJoin(replicas)

    df.cache()

    total_registros = df.count()
    total_municipios = df.select(countDistinct("MUNICIPIO")).collect()[0][0]
    total_anios = df.select(countDistinct("YEAR")).collect()[0][0]

    df_municipio = df.groupBy("MUNICIPIO") \
        .agg(spark_sum("DATO_NUMERICO").alias("TOTAL_CASOS_PROCESADOS")) \
        .orderBy(col("TOTAL_CASOS_PROCESADOS").desc())

    municipios_pd = df_municipio.toPandas()
    municipios_pd["TOTAL_CASOS_PROCESADOS"] = municipios_pd["TOTAL_CASOS_PROCESADOS"].round(2)
    guardar_csv_pandas(municipios_pd, "data/municipios_pyspark.csv")

    df_anio = df.groupBy("YEAR") \
        .agg(spark_sum("DATO_NUMERICO").alias("TOTAL_PROCESADO")) \
        .orderBy("YEAR")

    anios_pd = df_anio.toPandas()
    anios_pd["TOTAL_PROCESADO"] = anios_pd["TOTAL_PROCESADO"].round(2)
    guardar_csv_pandas(anios_pd, "data/anios_pyspark.csv")

    df_promedio = df.groupBy("MUNICIPIO") \
        .agg(avg("DATO_NUMERICO").alias("PROMEDIO_INDICADOR")) \
        .orderBy(col("PROMEDIO_INDICADOR").desc())

    promedios_pd = df_promedio.toPandas()
    promedios_pd["PROMEDIO_INDICADOR"] = promedios_pd["PROMEDIO_INDICADOR"].round(2)
    guardar_csv_pandas(promedios_pd, "data/promedios_pyspark.csv")

    df_cluster = df.groupBy("MUNICIPIO") \
        .agg(
            spark_sum("DATO_NUMERICO").alias("TOTAL_CASOS_PROCESADOS"),
            avg("DATO_NUMERICO").alias("PROMEDIO_INDICADOR")
        ) \
        .dropna()

    assembler = VectorAssembler(
        inputCols=["TOTAL_CASOS_PROCESADOS", "PROMEDIO_INDICADOR"],
        outputCol="features_raw"
    )

    data = assembler.transform(df_cluster)

    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withStd=True,
        withMean=True
    )

    scaler_model = scaler.fit(data)
    data_scaled = scaler_model.transform(data)

    kmeans = KMeans(k=3, seed=1, featuresCol="features", predictionCol="prediction")
    model = kmeans.fit(data_scaled)
    result = model.transform(data_scaled)

    evaluator = ClusteringEvaluator(
        featuresCol="features",
        predictionCol="prediction",
        metricName="silhouette"
    )

    silhouette = evaluator.evaluate(result)

    clusters_pd = result.select("MUNICIPIO", "TOTAL_CASOS_PROCESADOS", "PROMEDIO_INDICADOR", "prediction").toPandas()

    resumen_clusters = clusters_pd.groupby("prediction")["TOTAL_CASOS_PROCESADOS"].mean().sort_values()
    perfiles = {}
    nombres = ["Baja incidencia", "Media incidencia", "Alta incidencia"]

    for indice, cluster_id in enumerate(resumen_clusters.index):
        perfiles[cluster_id] = nombres[indice]

    clusters_pd["PERFIL_CLUSTER"] = clusters_pd["prediction"].map(perfiles)
    clusters_pd["TOTAL_CASOS_PROCESADOS"] = clusters_pd["TOTAL_CASOS_PROCESADOS"].round(2)
    clusters_pd["PROMEDIO_INDICADOR"] = clusters_pd["PROMEDIO_INDICADOR"].round(2)
    clusters_pd = clusters_pd.sort_values("TOTAL_CASOS_PROCESADOS", ascending=False)

    guardar_csv_pandas(clusters_pd, "data/clusters_pyspark.csv")

    inicio_pandas = time.time()

    df_pandas = pd.read_csv("data/seguridad_clean.csv")
    df_pandas = limpiar_pandas(df_pandas)

    if args.factor > 1:
        df_pandas = pd.concat([df_pandas] * args.factor, ignore_index=True)

    df_pandas.groupby("MUNICIPIO")["DATO_NUMERICO"].sum()

    tiempo_pandas = round(time.time() - inicio_pandas, 4)

    inicio_spark = time.time()

    df.groupBy("MUNICIPIO") \
        .agg(spark_sum("DATO_NUMERICO").alias("TOTAL_CASOS_PROCESADOS")) \
        .collect()

    tiempo_spark = round(time.time() - inicio_spark, 4)
    tiempo_total = round(time.time() - inicio_total, 4)

    ruta_tiempos = "data/tiempos_pyspark.csv"

    nueva_fila = pd.DataFrame([{
        "ESCENARIO": args.escenario,
        "MASTER": args.master,
        "FACTOR": args.factor,
        "TIEMPO_PANDAS": tiempo_pandas,
        "TIEMPO_SPARK": tiempo_spark,
        "TIEMPO_TOTAL": tiempo_total
    }])

    if os.path.exists(ruta_tiempos):
        tiempos = pd.read_csv(ruta_tiempos)
        if "ESCENARIO" in tiempos.columns:
            tiempos = tiempos[tiempos["ESCENARIO"] != args.escenario]
        tiempos = pd.concat([tiempos, nueva_fila], ignore_index=True)
    else:
        tiempos = nueva_fila

    guardar_csv_pandas(tiempos, ruta_tiempos)

    metricas = pd.DataFrame([
        {"METRICA": "Registros originales", "VALOR": registros_originales},
        {"METRICA": "Registros procesados con ampliación", "VALOR": total_registros},
        {"METRICA": "Factor de ampliación del dataset", "VALOR": args.factor},
        {"METRICA": "Configuración Spark utilizada", "VALOR": args.master},
        {"METRICA": "Municipios analizados", "VALOR": total_municipios},
        {"METRICA": "Años analizados", "VALOR": total_anios},
        {"METRICA": "Modelo MLlib aplicado", "VALOR": "KMeans"},
        {"METRICA": "Número de clusters", "VALOR": 3},
        {"METRICA": "Silhouette del modelo", "VALOR": round(silhouette, 4)}
    ])

    guardar_csv_pandas(metricas, "data/metricas_pyspark.csv")

    print("Archivos generados:")
    print("data/municipios_pyspark.csv")
    print("data/anios_pyspark.csv")
    print("data/promedios_pyspark.csv")
    print("data/clusters_pyspark.csv")
    print("data/tiempos_pyspark.csv")
    print("data/metricas_pyspark.csv")
    print(f"Master: {args.master}")
    print(f"Factor: {args.factor}")
    print(f"Registros procesados: {total_registros}")
    print(f"Tiempo Pandas: {tiempo_pandas}")
    print(f"Tiempo Spark: {tiempo_spark}")
    print(f"Tiempo total: {tiempo_total}")
    print(f"Silhouette: {round(silhouette, 4)}")

    spark.stop()


if __name__ == "__main__":
    main()