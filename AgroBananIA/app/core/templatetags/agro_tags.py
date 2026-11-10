from django import template

register = template.Library()

# Nombre en español y severidad de cada clase que entrega el modelo
ENFERMEDADES = {
    "banana black sigatoka disease": ("Sigatoka negra", "critical"),
    "banana yellow sigatoka disease": ("Sigatoka amarilla", "warning"),
    "banana moko disease": ("Moko", "critical"),
    "banana panama disease": ("Mal de Panamá", "critical"),
    "banana insect pest disease": ("Daño por plagas", "warning"),
    "banana healthy leaf": ("Hoja sana", "normal"),
}

SEVERIDAD_TEXTO = {
    "critical": "Requiere atención inmediata",
    "warning": "Monitoreo requerido",
    "normal": "Sin enfermedad detectada",
}


def _buscar(valor):
    return ENFERMEDADES.get(str(valor or "").strip().lower())


@register.filter
def nombre_es(valor):
    """'Banana Black Sigatoka Disease' -> 'Sigatoka negra'."""
    info = _buscar(valor)
    return info[0] if info else valor


@register.filter
def severidad(valor):
    """Clase CSS de severidad: critical, warning o normal."""
    info = _buscar(valor)
    return info[1] if info else "warning"


@register.filter
def severidad_texto(valor):
    return SEVERIDAD_TEXTO[severidad(valor)]


@register.filter
def css_num(valor, decimales=1):
    """Número con punto decimal para usar dentro de CSS/JS, sin importar el idioma."""
    try:
        return f"{float(valor):.{int(decimales)}f}"
    except (TypeError, ValueError):
        return "0"
