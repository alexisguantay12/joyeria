from django.contrib import admin
from .models import Categoria, Producto, Local, StockLocal, IngresoLote, MovimientoStock

# Admin para Categoria
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'created_at', 'updated_at')
    search_fields = ('nombre',)
    ordering = ('nombre',)

# Admin para Producto
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_venta', 'codigo', 'created_at', 'updated_at')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'descripcion', 'codigo')
    ordering = ('nombre',)
    readonly_fields = ('codigo',)  # Para evitar modificar el código que es único y generado

# Admin para Local
class LocalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'created_at', 'updated_at')
    search_fields = ('nombre',)
    ordering = ('nombre',)

# Admin para StockLocal
class StockLocalAdmin(admin.ModelAdmin):
    list_display = ('producto', 'local', 'cantidad')
    search_fields = ('producto__nombre', 'local__nombre')
    list_filter = ('local',)
    ordering = ('local', 'producto')

# Admin para IngresoLote
class IngresoLoteAdmin(admin.ModelAdmin):
    list_display = ('local', 'fecha')
    search_fields = ('local__nombre',)
    ordering = ('-fecha',)

# Admin para MovimientoStock
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('lote', 'producto', 'cantidad', 'tipo', 'created_at')
    search_fields = ('producto__nombre', 'lote__local__nombre')
    list_filter = ('tipo', 'lote__local')
    ordering = ('-created_at',)

# Registrar los modelos con sus respectivos admins
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Local, LocalAdmin)
admin.site.register(StockLocal, StockLocalAdmin)
admin.site.register(IngresoLote, IngresoLoteAdmin)
admin.site.register(MovimientoStock, MovimientoStockAdmin)
