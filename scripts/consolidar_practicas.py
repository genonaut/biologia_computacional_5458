"""
CONSOLIDAR PRÁCTICAS TIC A CSV
==============================

Este script busca todos los archivos CSV del alumnado en data/, ignora la
plantilla example_data.csv, valida su estructura y su contenido, y crea DOS
archivos CSV en resultados/:

1. practicas_TIC_consolidadas.csv
   Contiene únicamente las filas que superaron las validaciones.

2. errores_validacion.csv
   Contiene archivos o filas que deben revisarse, junto con la causa.

Estructura esperada:

biologia_computacional_5458/
├── data/
│   ├── example_data.csv
│   ├── bbustos.csv
│   └── ...
├── scripts/
│   └── consolidar_practicas_a_csv_comentado.py
└── resultados/                 <- se crea automáticamente

Ejecutar desde la raíz del repositorio:

    cd /Users/genonauta/Desktop/biologia_computacional_5458
    python3 scripts/consolidar_practicas_a_csv_comentado.py

Dependencia (se instala una sola vez):

    python3 -m pip install pandas
"""

from pathlib import Path
import sys
import pandas as pd


# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN
# -----------------------------------------------------------------------------

# Este es el esquema oficial que cada archivo de estudiante debe respetar.
# Los nombres deben coincidir exactamente, incluyendo mayúsculas y guiones bajos.
COLUMNAS_ESPERADAS = [
    "nombre",
    "apellido_paterno",
    "apellido_materno",
    "edad",
    "pronombres",
    "numero_de_cuenta",
    "inicio_practica_TIC",
    "final_practica_TIC",
]

# Rutas relativas a la carpeta raíz del proyecto.
CARPETA_DATOS = Path("data")
CARPETA_RESULTADOS = Path("resultados")
ARCHIVO_MOLDE = "example_data.csv"

# Archivos finales que generará el programa.
ARCHIVO_CONSOLIDADO = CARPETA_RESULTADOS / "practicas_TIC_consolidadas.csv"
ARCHIVO_ERRORES = CARPETA_RESULTADOS / "errores_validacion.csv"


# -----------------------------------------------------------------------------
# 2. ESTRUCTURAS PARA ACUMULAR RESULTADOS
# -----------------------------------------------------------------------------

# Aquí se guardarán las filas correctas de todos los estudiantes.
registros_validos = []

# Aquí se guardarán problemas de lectura, estructura o validación.
errores = []


# -----------------------------------------------------------------------------
# 3. COMPROBAR CARPETAS Y BUSCAR ENTREGAS
# -----------------------------------------------------------------------------

if not CARPETA_DATOS.exists():
    sys.exit(
        f"Error: no existe la carpeta '{CARPETA_DATOS}'. "
        "Ejecuta el script desde la raíz del proyecto."
    )

# Crear resultados/ si todavía no existe.
CARPETA_RESULTADOS.mkdir(exist_ok=True)

# Buscar CSV y excluir el archivo molde, que sólo contiene los encabezados.
archivos = sorted(
    archivo
    for archivo in CARPETA_DATOS.glob("*.csv")
    if archivo.name != ARCHIVO_MOLDE
)

if not archivos:
    sys.exit(
        "No se encontraron entregas. "
        "Agrega archivos CSV de estudiantes dentro de data/."
    )

print(f"Archivos CSV encontrados: {len(archivos)}")


# -----------------------------------------------------------------------------
# 4. LEER Y VALIDAR CADA CSV
# -----------------------------------------------------------------------------

for archivo in archivos:
    print(f"Procesando: {archivo.name}")

    try:
        # dtype=str evita perder ceros iniciales en numero_de_cuenta.
        # utf-8-sig es compatible con CSV creados por muchas aplicaciones.
        tabla = pd.read_csv(
            archivo,
            dtype=str,
            encoding="utf-8-sig"
        ).fillna("")

    except Exception as error:
        errores.append({
            "archivo": archivo.name,
            "fila": "",
            "tipo_error": "lectura",
            "detalle": f"No se pudo leer el CSV: {error}",
        })
        continue

    # Comprobar que las columnas del archivo coincidan con el formato oficial.
    columnas_reales = list(tabla.columns)

    faltantes = [
        columna for columna in COLUMNAS_ESPERADAS
        if columna not in columnas_reales
    ]

    adicionales = [
        columna for columna in columnas_reales
        if columna not in COLUMNAS_ESPERADAS
    ]

    if faltantes or adicionales:
        detalle = []

        if faltantes:
            detalle.append("Faltan columnas: " + ", ".join(faltantes))

        if adicionales:
            detalle.append(
                "Columnas no esperadas: " + ", ".join(adicionales)
            )

        errores.append({
            "archivo": archivo.name,
            "fila": "",
            "tipo_error": "estructura",
            "detalle": " | ".join(detalle),
        })
        continue

    if tabla.empty:
        errores.append({
            "archivo": archivo.name,
            "fila": "",
            "tipo_error": "contenido",
            "detalle": "El archivo contiene encabezados pero no registros.",
        })
        continue

    # Conservar únicamente columnas oficiales y en un orden predefinido.
    tabla = tabla[COLUMNAS_ESPERADAS].copy()

    # Trazabilidad: indicar de qué archivo y qué fila vino cada registro.
    tabla["archivo_origen"] = archivo.name
    tabla["fila_origen"] = range(2, len(tabla) + 2)

    # Crear columnas auxiliares para validar números y fechas.
    tabla["edad_numerica"] = pd.to_numeric(
        tabla["edad"],
        errors="coerce"
    )

    tabla["inicio_fecha"] = pd.to_datetime(
        tabla["inicio_practica_TIC"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    tabla["final_fecha"] = pd.to_datetime(
        tabla["final_practica_TIC"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    # Validar cada fila del archivo actual.
    for _, fila in tabla.iterrows():
        problemas = []

        # Campos mínimos que deben tener información.
        for columna in [
            "nombre",
            "apellido_paterno",
            "numero_de_cuenta",
            "inicio_practica_TIC",
            "final_practica_TIC",
        ]:
            if not fila[columna].strip():
                problemas.append(f"Campo obligatorio vacío: {columna}")

        # Edad: debe ser numérica y encontrarse en un rango razonable.
        if pd.isna(fila["edad_numerica"]):
            problemas.append("Edad no numérica o vacía")
        elif not 0 < fila["edad_numerica"] < 120:
            problemas.append("Edad fuera del rango válido: 1 a 119")

        # Fechas: deben tener el formato AAAA-MM-DD.
        if pd.isna(fila["inicio_fecha"]):
            problemas.append(
                "Fecha inicial inválida; usa el formato AAAA-MM-DD"
            )

        if pd.isna(fila["final_fecha"]):
            problemas.append(
                "Fecha final inválida; usa el formato AAAA-MM-DD"
            )

        # La práctica no puede terminar antes de comenzar.
        if (
            pd.notna(fila["inicio_fecha"])
            and pd.notna(fila["final_fecha"])
            and fila["final_fecha"] < fila["inicio_fecha"]
        ):
            problemas.append(
                "La fecha final es anterior a la fecha inicial"
            )

        if problemas:
            errores.append({
                "archivo": fila["archivo_origen"],
                "fila": fila["fila_origen"],
                "tipo_error": "validacion",
                "detalle": " | ".join(problemas),
            })
        else:
            registros_validos.append(fila.to_dict())


# -----------------------------------------------------------------------------
# 5. CREAR LA TABLA CONSOLIDADA
# -----------------------------------------------------------------------------

if registros_validos:
    practicas = pd.DataFrame(registros_validos)

    # Dejar edad como entero una vez que ha sido validada.
    practicas["edad"] = practicas["edad_numerica"].astype(int)

    # Calcular duración contando tanto el día de inicio como el día final.
    practicas["duracion_dias"] = (
        practicas["final_fecha"] - practicas["inicio_fecha"]
    ).dt.days + 1

    # Crear una columna cómoda para leer y ordenar en la tabla final.
    practicas["nombre_completo"] = (
        practicas["nombre"].str.strip()
        + " "
        + practicas["apellido_paterno"].str.strip()
        + " "
        + practicas["apellido_materno"].str.strip()
    ).str.replace(r"\s+", " ", regex=True).str.strip()

    # Ordenar cronológicamente y después alfabéticamente.
    practicas = practicas.sort_values(
        by=[
            "inicio_fecha",
            "final_fecha",
            "apellido_paterno",
            "nombre",
        ]
    )

    # IMPORTANTE:
    # inicio_fecha y final_fecha son datetime internos de pandas. Para evitar
    # que aparezca 00:00:00 al abrir el CSV, las convertimos de nuevo a texto
    # con formato explícito AAAA-MM-DD.
    practicas["inicio_practica_TIC"] = practicas[
        "inicio_fecha"
    ].dt.strftime("%Y-%m-%d")

    practicas["final_practica_TIC"] = practicas[
        "final_fecha"
    ].dt.strftime("%Y-%m-%d")

    # Elegimos las columnas finales y omitimos las auxiliares usadas únicamente
    # para validación (edad_numerica, inicio_fecha y final_fecha).
    COLUMNAS_SALIDA = [
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "nombre_completo",
        "edad",
        "pronombres",
        "numero_de_cuenta",
        "inicio_practica_TIC",
        "final_practica_TIC",
        "duracion_dias",
        "archivo_origen",
        "fila_origen",
    ]

    practicas = practicas[COLUMNAS_SALIDA]

else:
    # Si no hubo registros correctos, el CSV final conservará los encabezados.
    practicas = pd.DataFrame(columns=[
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "nombre_completo",
        "edad",
        "pronombres",
        "numero_de_cuenta",
        "inicio_practica_TIC",
        "final_practica_TIC",
        "duracion_dias",
        "archivo_origen",
        "fila_origen",
    ])

# Tabla para el reporte de problemas.
reporte_errores = pd.DataFrame(
    errores,
    columns=["archivo", "fila", "tipo_error", "detalle"]
)


# -----------------------------------------------------------------------------
# 6. EXPORTAR LOS RESULTADOS COMO CSV
# -----------------------------------------------------------------------------

# index=False evita crear una columna extra con el índice interno de pandas.
# encoding="utf-8-sig" ayuda a que Excel reconozca correctamente acentos al abrir
# el CSV directamente en macOS o Windows.
practicas.to_csv(
    ARCHIVO_CONSOLIDADO,
    index=False,
    encoding="utf-8-sig"
)

reporte_errores.to_csv(
    ARCHIVO_ERRORES,
    index=False,
    encoding="utf-8-sig"
)


# -----------------------------------------------------------------------------
# 7. INFORMAR EL RESULTADO
# -----------------------------------------------------------------------------

print("\nProceso terminado.")
print(f"CSV consolidado: {ARCHIVO_CONSOLIDADO}")
print(f"Reporte de errores: {ARCHIVO_ERRORES}")
print(f"Archivos CSV revisados: {len(archivos)}")
print(f"Registros válidos: {len(practicas)}")
print(f"Errores detectados: {len(reporte_errores)}")
