from django.db import models
from applications.core.models import BaseAbstractWithUser
# Create your models here.

# Manager personalizado
class VentaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Venta(BaseAbstractWithUser):  
    local = models.ForeignKey(
        'productos.Local',
        on_delete=models.PROTECT,
        verbose_name="Local de Venta"
    )
    fecha = models.DateTimeField(
        "Fecha de la Venta",
        auto_now_add=True
    )
    total = models.DecimalField(
        "Total",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']

    objects = VentaManager()

    all_objects = models.Manager()     # Todas (incluyendo eliminadas)

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    def calcular_total(self):
        print("Elemento paso total al resto")
        total = sum([detalle.subtotal for detalle in self.detalles.all()])
        print("Elemento paso total ")
        self.total = total
        self.save()


class DetalleVenta(BaseAbstractWithUser):
    venta = models.ForeignKey(
        'ventas.Venta',
        related_name='detalles',
        on_delete=models.CASCADE,
        verbose_name="Venta"
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    cantidad = models.IntegerField("Cantidad")
    precio_unitario = models.DecimalField(
        "Precio Unitario",
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    @property 
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (${self.precio_unitario})"