# core/utils.py

from django.core.mail import send_mail
from django.conf import settings

def enviar_notificacion_stock_cero(producto_nombre):
    """
    Envía una notificación por correo cuando el stock de un producto llega a 0.
    """
    subject = '🚨 Alerta de Stock Bajo: ¡Se agotó un producto!'
    message = (
        f'¡Hola!\n\n'
        f'El stock del producto "{producto_nombre}" ha llegado a 0 después de una venta.\n'
        f'Por favor, asegúrate de reabastecerlo pronto.\n\n'
        f'Este es un mensaje automático.'
    )
    from_email = settings.EMAIL_HOST_USER
    recipient_list = ['skuku390@gmail.com'] # Puedes poner aquí un correo o una lista

    try:
        send_mail(subject, message, from_email, recipient_list)
        print(f"Notificación de stock enviada para el producto: {producto_nombre}")
    except Exception as e:
        print(f"Error al enviar la notificación por correo: {e}")