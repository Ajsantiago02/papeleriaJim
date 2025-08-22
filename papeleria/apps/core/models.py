# papeleria/models.py

from django.db import models

# ======================================================================
# MODELOS DE INVENTARIO
# ======================================================================

class Categoria(models.Model):
    """
    Modelo para clasificar los productos (ej. "Cuadernos", "Lápices").
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    """
    Modelo para los productos que vendes.
    """
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=50, unique=True, blank=True, null=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    costo_compra = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.IntegerField(default=0)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True) # ¡El nuevo campo!

    def __str__(self):
        return self.nombre

        
# ======================================================================
# MODELOS DE VENTAS
# ======================================================================

class Venta(models.Model):
    """
    Modelo para registrar una transacción de venta completa.
    """
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha_venta.strftime('%d/%m/%Y %H:%M')}"

class DetalleVenta(models.Model):
    """
    Modelo para registrar cada producto dentro de una venta.
    """
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"