import os
import glob
import pandas as pd
from deepface import DeepFace
import argparse
import warnings

# Ignorar advertencias de TensorFlow que no son críticas
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Silenciar mensajes de información y advertencia de TensorFlow
# Nivel 0: Muestra todos los mensajes
# Nivel 1: Oculta mensajes de INFO
# Nivel 2: Oculta mensajes de INFO y WARNINGS
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

def analyze_emotions(input_dir):
    """
    Analiza todos los archivos de imagen en un directorio para detectar emociones.
    """
    if not os.path.isdir(input_dir):
        print(f"❌ Error: El directorio de entrada no existe: {input_dir}")
        return

    image_files = glob.glob(os.path.join(input_dir, '*.jpg'))
    if not image_files:
        image_files = glob.glob(os.path.join(input_dir, '*.png'))

    if not image_files:
        print(f"🤷 No se encontraron imágenes (.jpg, .png) en el directorio: {input_dir}")
        return

    print(f"🙂 Encontradas {len(image_files)} imágenes. Iniciando análisis emocional con DeepFace...")

    all_results_list = []

    try:
        results = DeepFace.analyze(
            img_path=image_files,
            actions=['emotion'],
            enforce_detection=False
        )

        # --- Bucle de procesamiento de resultados (NUEVA VERSIÓN MEJORADA) ---
        for single_image_results in results:
            if single_image_results:
                res = single_image_results[0]

                # Creamos un diccionario base con la información principal
                row = {
                    'archivo': os.path.basename(res.get('source', 'N/A')),
                    'emocion_dominante': res.get('dominant_emotion', 'N/A')
                }

                # Añadimos las puntuaciones de cada emoción al diccionario
                emotions = res.get('emotion', {})
                row.update(emotions)

                all_results_list.append(row)

        # Convertimos la lista de diccionarios a un DataFrame
        df = pd.DataFrame(all_results_list)

        # Reordenamos las columnas para que tengan un orden lógico
        if not df.empty:
            column_order = ['archivo', 'emocion_dominante', 'angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
            # Nos aseguramos de que solo usamos las columnas que realmente existen en el DataFrame
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]

            output_path = os.path.join(input_dir, '_emotions_analysis.csv')
            df.to_csv(output_path, index=False, sep=';') # Usamos punto y coma como separador para evitar problemas con comas en los números
            print(f"\n✅ Análisis completado. Resultados guardados en: {output_path}")
        else:
            print("\n⚠️ No se detectaron caras en ninguna de las imágenes procesadas.")

    except Exception as e:
        print(f"\n💥 Error durante el análisis con DeepFace: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analizador de Emociones con DeepFace")
    parser.add_argument("--input", required=True, help="Directorio que contiene los frames de vídeo a analizar.")
    args = parser.parse_args()

    analyze_emotions(args.input)
