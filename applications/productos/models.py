from django.db import models
import uuid
from applications.core.models import BaseAbstractWithUser 

# Categoría de productos (puede ser anillos, colgantes, etc.)

class ProductoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Categoria(BaseAbstractWithUser):
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de la categoría"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción de la categoría"
    )
    
    class Meta:
        db_table = 'categoria'  # Nombre de la tabla en la base de datos
    
    def __str__(self):
        return self.nombre

# Producto base
class Producto(BaseAbstractWithUser):
    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre del producto"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción del producto"
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio de venta"
    ) 
    gramos = models.IntegerField(
        default=1
    )
    codigo = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="Código único (QR / Código de barras)"
    )
    codigo_barras = models.ImageField(
        upload_to='barcodes/', 
        blank=True, 
        null=True
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Categoría del producto"
    )
    objects = ProductoManager()
    all_objects = models.Manager()     # Todas (incluyendo eliminadas)

    class Meta:
        db_table = 'productos'  # Nombre de la tabla en la base de datos

    def __str__(self):
        return f"{self.nombre} - ${self.precio_venta}"

class ImagenProducto(BaseAbstractWithUser):
    imagen = models.ImageField(
        upload_to='productos/',
        blank=True,
        null=True,
        verbose_name="Imagen del producto"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, 
        related_name='imagenes'
    )



class Local(BaseAbstractWithUser):
    nombre = models.CharField(
        max_length= 60,
        blank=True,
        null = True
    )
    class Meta:
        db_table = 'locales'  # Nombre de la tabla en la base de datos

    def __str__(self):
        return self.nombre

class StockLocal(BaseAbstractWithUser):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    local = models.ForeignKey(Local, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'local')


class IngresoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class IngresoLote(BaseAbstractWithUser):
    local = models.ForeignKey(Local, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length= 50,null=True,blank=True)

    objects = IngresoManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Lote #{self.id} - {self.local.nombre} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"

class MovimientoStock(BaseAbstractWithUser):
    lote = models.ForeignKey(IngresoLote, on_delete=models.CASCADE, related_name="movimientos")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    tipo = models.CharField(max_length=20, default='ingreso')  # Podés usar choices si querés más control

    def __str__(self):
        return f"{self.tipo.upper()} - {self.producto.nombre} ({self.cantidad})"