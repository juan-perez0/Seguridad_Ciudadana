from pyspark.sql import SparkSession
from pyspark.sql.functions import sum, avg, col, regexp_replace
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
import pandas as pd
import time

# -----------------------------
# 🔹 INICIAR SPARK
# -----------------------------
spark = SparkSession.builder \
    .appName("Seguridad_Cundinamarca") \
    .master("local[*]") \
    .getOrCreate()

print("✅ Spark funcionando")

# -----------------------------
# 🔹 CARGAR DATOS
# -----------------------------
df = spark.read.csv("data/seguridad_clean.csv", header=True, inferSchema=True)

print("📊 Datos cargados")

# -----------------------------
# 🔥 LIMPIEZA COMPLETA (CLAVE)
# -----------------------------
# 🔹 LIMPIEZA CORRECTA (SIN DAÑAR DATOS)
df = df.withColumn(
    "DATO_NUMERICO",
    regexp_replace(col("DATO_NUMERICO"), ",", "")
)

df = df.withColumn(
    "DATO_NUMERICO",
    col("DATO_NUMERICO").cast("double")
)

df = df.dropna(subset=["DATO_NUMERICO"])

# -----------------------------
# 🔹 AGRUPACIÓN POR MUNICIPIO
# -----------------------------
print("🚀 Calculando casos por municipio...")

df_municipio = df.groupBy("MUNICIPIO") \
    .agg(sum("DATO_NUMERICO").alias("TOTAL_CASOS")) \
    .orderBy("TOTAL_CASOS", ascending=False)

df_municipio = df_municipio.withColumn(
    "TOTAL_CASOS", col("TOTAL_CASOS").cast("long")
)

df_municipio.toPandas().to_csv("data/municipios_pyspark.csv", index=False)

print("💾 municipios_pyspark.csv generado")

# -----------------------------
# 🔹 AGRUPACIÓN POR AÑO
# -----------------------------
print("📅 Calculando casos por año...")

df_anio = df.groupBy("YEAR") \
    .agg(sum("DATO_NUMERICO").alias("TOTAL")) \
    .orderBy("YEAR")

df_anio = df_anio.withColumn(
    "TOTAL", col("TOTAL").cast("long")
)

df_anio.toPandas().to_csv("data/anios_pyspark.csv", index=False)

print("💾 anios_pyspark.csv generado")

# -----------------------------
# 🔹 PROMEDIO POR MUNICIPIO
# -----------------------------
print("📊 Calculando promedio...")

df_promedio = df.groupBy("MUNICIPIO") \
    .agg(avg("DATO_NUMERICO").alias("PROMEDIO"))

df_promedio.toPandas().to_csv("data/promedios_pyspark.csv", index=False)

print("💾 promedios_pyspark.csv generado")

# -----------------------------
# 🔹 CLUSTERING (ML)
# -----------------------------
print("🤖 Iniciando clustering...")

# 🔥 USAR DATOS AGRUPADOS (CLAVE)
df_cluster = df.groupBy("MUNICIPIO") \
    .agg(sum("DATO_NUMERICO").alias("TOTAL_CASOS"))

# asegurar tipo correcto
df_cluster = df_cluster.withColumn(
    "TOTAL_CASOS", col("TOTAL_CASOS").cast("double")
)

# vector
assembler = VectorAssembler(
    inputCols=["TOTAL_CASOS"],
    outputCol="features"
)

data = assembler.transform(df_cluster)

# modelo
kmeans = KMeans(k=3, seed=1)
model = kmeans.fit(data)

result = model.transform(data)

# exportar limpio
result.select("MUNICIPIO", "TOTAL_CASOS", "prediction") \
    .toPandas() \
    .to_csv("data/clusters_pyspark.csv", index=False)

print("💾 clusters_pyspark.csv generado")
# -----------------------------
# 🔹 COMPARACIÓN DE TIEMPOS
# -----------------------------
print("\n⏱️ Comparando tiempos...")

# Pandas
start = time.time()

df_pandas = pd.read_csv("data/seguridad_clean.csv")

# misma limpieza en pandas
df_pandas["DATO_NUMERICO"] = (
    df_pandas["DATO_NUMERICO"]
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)

df_pandas["DATO_NUMERICO"] = pd.to_numeric(df_pandas["DATO_NUMERICO"], errors="coerce")

pandas_result = df_pandas.groupby("MUNICIPIO")["DATO_NUMERICO"].sum()

end = time.time()
pandas_time = end - start

print(f"🐼 Tiempo Pandas: {pandas_time:.4f} segundos")

# Spark
start = time.time()

df.groupBy("MUNICIPIO") \
    .agg(sum("DATO_NUMERICO")) \
    .collect()

end = time.time()
spark_time = end - start

print(f"⚡ Tiempo Spark: {spark_time:.4f} segundos")

# -----------------------------
# 🔹 FINAL
# -----------------------------
print("\n🎯 TODO COMPLETADO")

input("Presiona ENTER para salir...")