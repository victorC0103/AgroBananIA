import os
import logging
import traceback
import numpy as np
import cv2
import uuid
from django.conf import settings
import tensorflow as tf
from keras import preprocessing, models
from tensorflow.keras.applications.resnet50 import preprocess_input as preprocess_input_resnet50
    
logger = logging.getLogger(__name__)


MODEL_DIR = os.path.join(settings.BASE_DIR, 'static', 'models')


class_mapping = {
    0: "Banana Black Sigatoka Disease",
    1: "Banana Healthy Leaf",
    2: "Banana Insect Pest Disease",
    3: "Banana Moko Disease",
    4: "Banana Panama Disease",
    5: "Banana Yellow Sigatoka Disease",
}


recomendaciones_mapping = {
    0: "Retirar y destruir hojas gravemente afectadas. Aplicar fungicidas sistémicos y de contacto.",
    1: "La planta está sana. Continuar con buenas prácticas de manejo agronómico.",
    2: "Identificar y aplicar insecticidas específicos. Implementar manejo integrado de plagas (MIP).",
    3: "Eliminar plantas infectadas. Desinfectar herramientas y evitar riego contaminado.",
    4: "Eliminar y destruir plantas afectadas. Implementar cuarentena y usar variedades resistentes.",
    5: "Aplicar fungicidas preventivos y curativos. Mantener el cultivo bien aireado.",
}



def load_resnet50_model():
    model_path = os.path.join(MODEL_DIR, 'model_resnet50_final_optimized.keras')
    try:
        model = models.load_model(model_path, compile=False)
        logger.info(f"✅ Modelo ResNet50 cargado correctamente: {model_path}")
        return model
    except Exception as e:
        logger.error(f"❌ Error al cargar ResNet50: {e}")
        logger.debug(traceback.format_exc())
        return None


model_resnet50 = load_resnet50_model()


if model_resnet50 is not None:
    logger.info("✅ Modelo ResNet50 cargado exitosamente y listo para usar")
else:
    logger.critical("❌ El modelo ResNet50 NO se cargó correctamente. El sistema no puede funcionar.")


def preprocess_image_resnet50(image_path, target_size=(224, 224)):

    try:
        img = preprocessing.image.load_img(image_path, target_size=target_size)
        img_array = preprocessing.image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input_resnet50(img_array) 

        logger.debug(f"ResNet50 - Rango de valores: [{img_array.min():.2f}, {img_array.max():.2f}]")
        return img_array
    except Exception as e:
        logger.error(f"❌ Error en preprocesamiento ResNet50: {e}")
        raise



def predict_with_resnet50(image_path):
    if model_resnet50 is None:
        raise RuntimeError("El modelo ResNet50 no está cargado correctamente.")
    
    try:
        img = preprocess_image_resnet50(image_path, target_size=(224, 224))
        pred = model_resnet50.predict(img, verbose=0)
        pred = np.squeeze(pred)
        
        if pred.ndim == 1:
            pred_probs = pred
        else:
            pred_probs = pred[0]
        
        pred_class = int(np.argmax(pred_probs))
        confidence = float(np.max(pred_probs))
        
        detailed_results = {}
        for class_id, class_name in class_mapping.items():
            prob = float(pred_probs[class_id])
            detailed_results[class_name] = {
                'class_id': class_id,
                'probability': prob,
                'confidence_percent': round(prob * 100, 2)
            }
        
        logger.info(f"✅ ResNet50 - Clase: {pred_class} ({class_mapping[pred_class]}), Confianza: {confidence:.4f}")
        logger.debug(f"   Probabilidades por clase: {detailed_results}")
        
        return pred_class, pred_probs, confidence, detailed_results
    
    except Exception as e:
        logger.exception("❌ Error durante la predicción con ResNet50: %s", e)
        raise RuntimeError("Error al predecir con el modelo ResNet50.")

def segment_and_save(image_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img = cv2.imread(image_path)
    
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 90, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    contoured = img_rgb.copy()
    cv2.drawContours(contoured, contours, -1, (255, 0, 0), 2)
    
    heatmap = np.zeros_like(img_rgb)
    heatmap[:, :, 0] = mask
    overlay = cv2.addWeighted(img_rgb, 0.7, heatmap, 0.6, 0)
    
    only_damage = cv2.bitwise_and(img_rgb, img_rgb, mask=mask)
    
    uid = uuid.uuid4().hex
    paths = {
        "contorno": os.path.join(output_dir, f"{uid}_contour.jpg"),
        "overlay": os.path.join(output_dir, f"{uid}_overlay.jpg"),
        "damage": os.path.join(output_dir, f"{uid}_damage.jpg"),
    }
    
    cv2.imwrite(paths["contorno"], cv2.cvtColor(contoured, cv2.COLOR_RGB2BGR))
    cv2.imwrite(paths["overlay"], cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    cv2.imwrite(paths["damage"], cv2.cvtColor(only_damage, cv2.COLOR_RGB2BGR))
    
    return paths


def obtener_nombre_enfermedad(diagnostico):
    if diagnostico is None:
        return "Enfermedad desconocida"
    try:
        key = int(diagnostico)
    except (ValueError, TypeError):
        key = None
    nombre = class_mapping.get(key)
    if nombre is None:
        logger.warning("Clave de diagnóstico no encontrada en class_mapping: %s", diagnostico)
        return "Enfermedad desconocida"
    return nombre


def obtener_recomendaciones(diagnostico):
    if diagnostico is None:
        return "Recomendación no disponible."
    try:
        key = int(diagnostico)
    except (ValueError, TypeError):
        key = None
    return recomendaciones_mapping.get(key, "Recomendaciones no disponibles.")


def get_model_info():
    if model_resnet50 is not None:
        return {
            'ResNet50': {
                'status': 'Cargado',
                'input_size': '224x224',
                'preprocessing': 'ResNet50 preprocess_input (modo caffe: RGB->BGR + zero-center)',
                'description': 'Modelo optimizado para clasificación de enfermedades de banano'
            }
        }
    else:
        return {
            'ResNet50': {
                'status': 'Error - No cargado',
                'input_size': '224x224',
                'preprocessing': 'N/A',
                'description': 'Modelo no disponible'
            }
        }
