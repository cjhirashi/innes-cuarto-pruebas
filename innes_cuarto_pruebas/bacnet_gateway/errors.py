# innes_cuarto_pruebas/bacnet_gateway/errors.py


class BACnetGatewayError(Exception):
    """Clase base para todos los errores del gateway BACnet."""


class DeviceTimeoutError(BACnetGatewayError):
    """Se levanta cuando discovery o un dispositivo no responde."""


class PropertyReadError(BACnetGatewayError):
    """Se levanta cuando falla la lectura de un objeto específico."""


class PropertyWriteError(BACnetGatewayError):
    """Se levanta cuando falla la escritura/liberación de un objeto específico."""